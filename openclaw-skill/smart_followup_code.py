import os
import json
from datetime import datetime

def run(params):
    max_replies = params.get("max_replies", 10)
    auto_send = params.get("auto_send", False)

    results = {
        "timestamp": datetime.now().isoformat(),
        "replies_processed": [],
        "hot_leads": [],
        "actions_taken": []
    }

    # Step 1: Read Gmail replies
    try:
        gmail_result = run_skill("gmail_check_replies", {"max_results": max_replies})
        if not gmail_result.get("success"):
            return {"success": False, "error": "Failed to read Gmail replies", "detail": gmail_result}
        replies = gmail_result.get("replies", [])
    except Exception as e:
        return {"success": False, "error": f"Gmail read failed: {str(e)}"}

    if not replies:
        results["summary"] = "No new replies found"
        results["success"] = True
        return results

    # Step 2: Process each reply
    for reply in replies:
        sender = reply.get("from", "unknown")
        subject = reply.get("subject", "")
        snippet = reply.get("snippet", "")
        message_id = reply.get("id", "")

        # Step 3: Read full body
        body = snippet
        try:
            body_result = run_skill("gmail_read_body", {"message_id": message_id})
            if body_result.get("success"):
                body = body_result.get("body", snippet)
        except:
            pass

        # Step 4: Classify intent
        intent = "UNKNOWN"
        try:
            groq_result = run_skill("groq_analyze", {
                "content": body[:500],
                "task": "Classify email reply intent as exactly one of: HOT, WARM, OBJECTION, COLD, IGNORE. HOT=ready to buy or very engaged. WARM=interested but needs more info. OBJECTION=has specific barrier. COLD=polite no. IGNORE=auto-reply or spam. Reply with only the classification word."
            })
            if groq_result.get("success"):
                raw = groq_result.get("analysis", "").strip().upper()
                for label in ["HOT", "WARM", "OBJECTION", "COLD", "IGNORE"]:
                    if label in raw:
                        intent = label
                        break
        except Exception as e:
            intent = "UNKNOWN"

        # Step 5: Generate follow-up based on intent
        followup_draft = None
        if intent in ["HOT", "WARM", "OBJECTION"]:
            try:
                if intent == "HOT":
                    prompt = f"Prospect replied positively to cold email about AI automation. Draft SHORT follow-up (3-4 sentences): confirm interest, propose 20-min call this week. No fluff. Their reply: {body[:300]}"
                elif intent == "WARM":
                    prompt = f"Prospect replied with questions about AI automation services. Draft SHORT follow-up (4-5 sentences): answer implied question, add one proof point, soft CTA. Their reply: {body[:300]}"
                else:
                    prompt = f"Prospect raised objection to AI automation cold email. Draft SHORT empathetic response (3-4 sentences): acknowledge concern, reframe, keep door open. Their reply: {body[:300]}"

                draft_result = run_skill("groq_chat", {
                    "message": prompt,
                    "system": "You are Wave, a strategic AI. Write direct professional emails. No emojis. No fluff. Every word earns its place."
                })
                if draft_result.get("success"):
                    followup_draft = draft_result.get("response", "")
            except Exception as e:
                followup_draft = f"Draft generation failed: {str(e)}"

        # Step 6: Update prospect in DB
        try:
            run_skill("db_update_prospect", {
                "email": sender,
                "status": intent,
                "notes": f"Reply received {datetime.now().strftime('%Y-%m-%d')}: {body[:200]}"
            })
        except:
            pass

        # Step 7: Auto-send if HOT and auto_send enabled
        sent = False
        if intent == "HOT" and auto_send and followup_draft:
            try:
                send_result = run_skill("gmail_send", {
                    "to": sender,
                    "subject": f"Re: {subject}",
                    "body": followup_draft
                })
                sent = send_result.get("success", False)
            except:
                pass

        reply_record = {
            "sender": sender,
            "subject": subject,
            "intent": intent,
            "body_preview": body[:200],
            "followup_draft": followup_draft,
            "sent": sent
        }

        results["replies_processed"].append(reply_record)
        if intent == "HOT":
            results["hot_leads"].append(sender)
        if sent:
            results["actions_taken"].append(f"Auto-sent follow-up to {sender} (HOT lead)")

        # Journal hot leads
        if intent == "HOT":
            try:
                run_skill("wave_journal", {
                    "entry": f"HOT LEAD: {sender} replied to outreach. Subject: {subject}. Preview: {body[:150]}"
                })
            except:
                pass

    results["success"] = True
    results["total_replies"] = len(replies)
    results["hot_count"] = len(results["hot_leads"])
    results["summary"] = f"Processed {len(replies)} replies. HOT: {len(results['hot_leads'])}. Actions: {len(results['actions_taken'])}."

    return results
