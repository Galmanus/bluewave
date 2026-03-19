import { FormEvent, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Webhook,
  Key,
  Plus,
  Trash2,
  Copy,
  Check,
  ToggleLeft,
  ToggleRight,
} from "lucide-react";
import {
  useWebhooks,
  useCreateWebhook,
  useDeleteWebhook,
  useUpdateWebhook,
  useAPIKeys,
  useCreateAPIKey,
  useRevokeAPIKey,
} from "../hooks/useIntegrations";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { ConfirmDialog } from "../components/ui/Dialog";

export default function IntegrationsPage() {
  // Webhooks
  const { data: webhooks, isLoading: whLoading } = useWebhooks();
  const createWebhook = useCreateWebhook();
  const deleteWebhook = useDeleteWebhook();
  const updateWebhook = useUpdateWebhook();
  const [showWhForm, setShowWhForm] = useState(false);
  const [whName, setWhName] = useState("");
  const [whUrl, setWhUrl] = useState("");
  const [whSecret, setWhSecret] = useState("");
  const [whEvents, setWhEvents] = useState("*");

  // API Keys
  const { data: apiKeys, isLoading: akLoading } = useAPIKeys();
  const createAPIKey = useCreateAPIKey();
  const revokeAPIKey = useRevokeAPIKey();
  const [showAkForm, setShowAkForm] = useState(false);
  const [akName, setAkName] = useState("");
  const [newKey, setNewKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Delete dialogs
  const [deleteWh, setDeleteWh] = useState<string | null>(null);
  const [revokeAk, setRevokeAk] = useState<string | null>(null);

  function handleCreateWebhook(e: FormEvent) {
    e.preventDefault();
    createWebhook.mutate(
      { name: whName, url: whUrl, secret: whSecret || undefined, events: whEvents },
      {
        onSuccess: () => {
          setShowWhForm(false);
          setWhName("");
          setWhUrl("");
          setWhSecret("");
          setWhEvents("*");
        },
      }
    );
  }

  function handleCreateAPIKey(e: FormEvent) {
    e.preventDefault();
    createAPIKey.mutate(
      { name: akName },
      {
        onSuccess: (data) => {
          setNewKey(data.key);
          setAkName("");
          setShowAkForm(false);
        },
      }
    );
  }

  function copyKey() {
    if (newKey) {
      navigator.clipboard.writeText(newKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <div className="space-y-3xl">
      {/* === API Keys === */}
      <section>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-display text-text-primary">API Keys</h2>
            {apiKeys && <Badge>{apiKeys.length}</Badge>}
          </div>
          <Button onClick={() => setShowAkForm(!showAkForm)}>
            <Plus className="h-4 w-4" strokeWidth={1.5} />
            Create key
          </Button>
        </div>
        <p className="mt-2 text-body text-text-secondary">
          Use API keys to connect Bluewave with OpenClaw, Zapier, or custom integrations.
        </p>

        {/* New key display */}
        <AnimatePresence>
          {newKey && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-lg"
            >
              <Card className="border-success/30 bg-success-subtle p-lg">
                <p className="text-body-medium text-text-primary">
                  Your new API key (save it now — it won't be shown again):
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <code className="flex-1 rounded bg-surface px-3 py-2 font-mono text-body text-text-primary">
                    {newKey}
                  </code>
                  <Button variant="secondary" size="sm" onClick={copyKey}>
                    {copied ? (
                      <Check className="h-4 w-4 text-success" />
                    ) : (
                      <Copy className="h-4 w-4" strokeWidth={1.5} />
                    )}
                  </Button>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="mt-2"
                  onClick={() => setNewKey(null)}
                >
                  Dismiss
                </Button>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Create form */}
        <AnimatePresence>
          {showAkForm && (
            <motion.form
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              onSubmit={handleCreateAPIKey}
              className="mt-lg overflow-hidden rounded-lg border border-border bg-surface p-lg"
            >
              <div className="flex gap-3">
                <div className="flex-1">
                  <Input
                    label="Key name"
                    required
                    value={akName}
                    onChange={(e) => setAkName(e.target.value)}
                    placeholder="e.g. OpenClaw Production"
                  />
                </div>
                <div className="flex items-end">
                  <Button type="submit" loading={createAPIKey.isPending}>
                    Create
                  </Button>
                </div>
              </div>
            </motion.form>
          )}
        </AnimatePresence>

        {/* Key list */}
        <div className="mt-lg space-y-2">
          {akLoading ? (
            <div className="h-16 animate-pulse rounded-lg bg-border-subtle" />
          ) : apiKeys && apiKeys.length > 0 ? (
            apiKeys.map((k) => (
              <Card key={k.id} className="flex items-center justify-between p-md">
                <div className="flex items-center gap-3">
                  <Key className="h-4 w-4 text-text-tertiary" strokeWidth={1.5} />
                  <div>
                    <p className="text-body-medium text-text-primary">{k.name}</p>
                    <p className="text-caption text-text-tertiary">
                      {k.key_prefix}••• · {k.is_active ? "Active" : "Revoked"}
                      {k.last_used_at && ` · Last used ${new Date(k.last_used_at).toLocaleDateString()}`}
                    </p>
                  </div>
                </div>
                {k.is_active && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-danger"
                    onClick={() => setRevokeAk(k.id)}
                  >
                    Revoke
                  </Button>
                )}
              </Card>
            ))
          ) : (
            <p className="py-xl text-center text-body text-text-tertiary">
              No API keys yet. Create one to connect OpenClaw or other integrations.
            </p>
          )}
        </div>
      </section>

      {/* === Webhooks === */}
      <section>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-heading text-text-primary">Webhooks</h2>
            {webhooks && <Badge>{webhooks.length}</Badge>}
          </div>
          <Button variant="secondary" onClick={() => setShowWhForm(!showWhForm)}>
            <Plus className="h-4 w-4" strokeWidth={1.5} />
            Add webhook
          </Button>
        </div>
        <p className="mt-2 text-body text-text-secondary">
          Receive real-time notifications when assets are uploaded, approved, or rejected.
        </p>

        {/* Create form */}
        <AnimatePresence>
          {showWhForm && (
            <motion.form
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              onSubmit={handleCreateWebhook}
              className="mt-lg overflow-hidden rounded-lg border border-border bg-surface p-lg space-y-lg"
            >
              <div className="grid grid-cols-1 gap-lg sm:grid-cols-2">
                <Input
                  label="Name"
                  required
                  value={whName}
                  onChange={(e) => setWhName(e.target.value)}
                  placeholder="e.g. OpenClaw"
                />
                <Input
                  label="URL"
                  required
                  type="url"
                  value={whUrl}
                  onChange={(e) => setWhUrl(e.target.value)}
                  placeholder="https://your-server/hooks/bluewave"
                />
                <Input
                  label="Secret (optional)"
                  value={whSecret}
                  onChange={(e) => setWhSecret(e.target.value)}
                  placeholder="HMAC signing secret"
                />
                <Input
                  label="Events"
                  value={whEvents}
                  onChange={(e) => setWhEvents(e.target.value)}
                  placeholder="* or asset.approved,asset.rejected"
                />
              </div>
              <Button type="submit" loading={createWebhook.isPending}>
                Create webhook
              </Button>
            </motion.form>
          )}
        </AnimatePresence>

        {/* Webhook list */}
        <div className="mt-lg space-y-2">
          {whLoading ? (
            <div className="h-16 animate-pulse rounded-lg bg-border-subtle" />
          ) : webhooks && webhooks.length > 0 ? (
            webhooks.map((wh) => (
              <Card
                key={wh.id}
                className="flex items-center justify-between p-md group"
              >
                <div className="flex items-center gap-3">
                  <Webhook className="h-4 w-4 text-text-tertiary" strokeWidth={1.5} />
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-body-medium text-text-primary">{wh.name}</p>
                      <Badge variant={wh.is_active ? "approved" : "draft"} dot>
                        {wh.is_active ? "Active" : "Paused"}
                      </Badge>
                    </div>
                    <p className="text-caption text-text-tertiary">
                      {wh.url} · Events: {wh.events}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      updateWebhook.mutate({
                        id: wh.id,
                        is_active: !wh.is_active,
                      })
                    }
                  >
                    {wh.is_active ? (
                      <ToggleRight className="h-4 w-4 text-success" />
                    ) : (
                      <ToggleLeft className="h-4 w-4 text-text-tertiary" />
                    )}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-danger"
                    onClick={() => setDeleteWh(wh.id)}
                  >
                    <Trash2 className="h-4 w-4" strokeWidth={1.5} />
                  </Button>
                </div>
              </Card>
            ))
          ) : (
            <p className="py-xl text-center text-body text-text-tertiary">
              No webhooks configured. Add one to receive real-time events.
            </p>
          )}
        </div>
      </section>

      {/* Delete webhook dialog */}
      <ConfirmDialog
        open={!!deleteWh}
        onOpenChange={(open) => !open && setDeleteWh(null)}
        title="Delete webhook"
        description="This webhook will stop receiving events immediately."
        confirmLabel="Delete"
        variant="danger"
        loading={deleteWebhook.isPending}
        onConfirm={() => {
          if (deleteWh) {
            deleteWebhook.mutate(deleteWh, {
              onSuccess: () => setDeleteWh(null),
            });
          }
        }}
      />

      {/* Revoke API key dialog */}
      <ConfirmDialog
        open={!!revokeAk}
        onOpenChange={(open) => !open && setRevokeAk(null)}
        title="Revoke API key"
        description="Any integration using this key will immediately lose access."
        confirmLabel="Revoke"
        variant="danger"
        loading={revokeAPIKey.isPending}
        onConfirm={() => {
          if (revokeAk) {
            revokeAPIKey.mutate(revokeAk, {
              onSuccess: () => setRevokeAk(null),
            });
          }
        }}
      />
    </div>
  );
}
