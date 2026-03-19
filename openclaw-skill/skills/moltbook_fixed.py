"""moltbook_fixed — auto-generated skill by Wave.

Fixed Moltbook skill with proper error handling
"""

import httpx
import json
import asyncio
from urllib.parse import urlencode

BASE_URL = "https://moltbook.com"

async def moltbook_home_handler(params: dict) -> dict:
    """Check Moltbook dashboard"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{BASE_URL}/api/home")
            if response.status_code == 200:
                data = response.json()
                return {"success": True, "data": data, "message": f"Dashboard loaded. Karma: {data.get('karma', 0)}"}
            else:
                return {"success": False, "data": None, "message": f"API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "data": None, "message": f"Connection error: {str(e)}"}

async def moltbook_feed_handler(params: dict) -> dict:
    """Browse Moltbook feed"""
    try:
        submolt = params.get('submolt')
        sort = params.get('sort', 'hot')
        limit = params.get('limit', 10)
        
        url = f"{BASE_URL}/api/feed"
        query_params = {'sort': sort, 'limit': str(limit)}
        if submolt:
            query_params['submolt'] = submolt
        
        full_url = f"{url}?{urlencode(query_params)}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(full_url)
            if response.status_code == 200:
                data = response.json()
                posts = data.get('posts', [])
                return {"success": True, "data": posts, "message": f"Found {len(posts)} posts"}
            else:
                return {"success": False, "data": None, "message": f"API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "data": None, "message": f"Error: {str(e)}"}

async def moltbook_post_handler(params: dict) -> dict:
    """Post to Moltbook"""
    try:
        title = params.get('title', '')
        content = params.get('content', '')
        submolt = params.get('submolt', 'general')
        
        if not title:
            return {"success": False, "data": None, "message": "Title is required"}
        
        payload = {
            'title': title,
            'content': content,
            'submolt': submolt
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{BASE_URL}/api/posts", json=payload)
            if response.status_code == 201:
                data = response.json()
                return {"success": True, "data": data, "message": f"Posted to m/{submolt}"}
            else:
                return {"success": False, "data": None, "message": f"Post failed: {response.status_code}"}
    except Exception as e:
        return {"success": False, "data": None, "message": f"Error: {str(e)}"}

async def moltbook_comment_handler(params: dict) -> dict:
    """Comment on a post"""
    try:
        post_id = params.get('post_id')
        content = params.get('content', '')
        parent_id = params.get('parent_id')
        
        if not post_id or not content:
            return {"success": False, "data": None, "message": "post_id and content required"}
        
        payload = {'content': content}
        if parent_id:
            payload['parent_id'] = parent_id
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{BASE_URL}/api/posts/{post_id}/comments", json=payload)
            if response.status_code == 201:
                return {"success": True, "data": response.json(), "message": "Comment posted"}
            else:
                return {"success": False, "data": None, "message": f"Comment failed: {response.status_code}"}
    except Exception as e:
        return {"success": False, "data": None, "message": f"Error: {str(e)}"}

async def moltbook_upvote_handler(params: dict) -> dict:
    """Upvote a post"""
    try:
        post_id = params.get('post_id')
        if not post_id:
            return {"success": False, "data": None, "message": "post_id required"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{BASE_URL}/api/posts/{post_id}/upvote")
            if response.status_code == 200:
                return {"success": True, "data": None, "message": "Upvoted"}
            else:
                return {"success": False, "data": None, "message": f"Upvote failed: {response.status_code}"}
    except Exception as e:
        return {"success": False, "data": None, "message": f"Error: {str(e)}"}

async def moltbook_follow_handler(params: dict) -> dict:
    """Follow an agent"""
    try:
        agent_name = params.get('agent_name')
        if not agent_name:
            return {"success": False, "data": None, "message": "agent_name required"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{BASE_URL}/api/follow", json={'agent': agent_name})
            if response.status_code == 200:
                return {"success": True, "data": None, "message": f"Following {agent_name}"}
            else:
                return {"success": False, "data": None, "message": f"Follow failed: {response.status_code}"}
    except Exception as e:
        return {"success": False, "data": None, "message": f"Error: {str(e)}"}

TOOLS = [
    {
        'name': 'moltbook_home_fixed',
        'description': 'Check Moltbook dashboard (fixed version)',
        'handler': moltbook_home_handler,
        'parameters': {}
    },
    {
        'name': 'moltbook_feed_fixed', 
        'description': 'Browse Moltbook feed (fixed version)',
        'handler': moltbook_feed_handler,
        'parameters': {
            'properties': {
                'submolt': {'type': 'string', 'description': 'Filter by submolt'},
                'sort': {'type': 'string', 'enum': ['hot', 'new', 'top'], 'default': 'hot'},
                'limit': {'type': 'integer', 'default': 10}
            },
            'type': 'object'
        }
    },
    {
        'name': 'moltbook_post_fixed',
        'description': 'Post to Moltbook (fixed version)', 
        'handler': moltbook_post_handler,
        'parameters': {
            'properties': {
                'title': {'type': 'string', 'description': 'Post title'},
                'content': {'type': 'string', 'description': 'Post content'},
                'submolt': {'type': 'string', 'default': 'general'}
            },
            'required': ['title'],
            'type': 'object'
        }
    },
    {
        'name': 'moltbook_comment_fixed',
        'description': 'Comment on post (fixed version)',
        'handler': moltbook_comment_handler,
        'parameters': {
            'properties': {
                'post_id': {'type': 'string', 'description': 'Post ID'},
                'content': {'type': 'string', 'description': 'Comment content'},
                'parent_id': {'type': 'string', 'description': 'Parent comment ID for replies'}
            },
            'required': ['post_id', 'content'],
            'type': 'object'
        }
    },
    {
        'name': 'moltbook_upvote_fixed',
        'description': 'Upvote a post (fixed version)',
        'handler': moltbook_upvote_handler,
        'parameters': {
            'properties': {
                'post_id': {'type': 'string', 'description': 'Post ID to upvote'}
            },
            'required': ['post_id'],
            'type': 'object'
        }
    },
    {
        'name': 'moltbook_follow_fixed',
        'description': 'Follow an agent (fixed version)',
        'handler': moltbook_follow_handler,
        'parameters': {
            'properties': {
                'agent_name': {'type': 'string', 'description': 'Agent name to follow'}
            },
            'required': ['agent_name'],
            'type': 'object'
        }
    }
]