import { FormEvent, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { UserPlus, Trash2, ChevronUp } from "lucide-react";
import {
  useUsers,
  useCreateUser,
  useUpdateUserRole,
  useDeleteUser,
} from "../hooks/useUsers";
import { useAuth } from "../contexts/AuthContext";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Badge } from "../components/ui/Badge";
import { Avatar } from "../components/ui/Avatar";
import { ConfirmDialog } from "../components/ui/Dialog";

const ROLES = ["admin", "editor", "viewer"] as const;

export default function TeamPage() {
  const { user: currentUser } = useAuth();
  const { data: users, isLoading } = useUsers();
  const createUser = useCreateUser();
  const updateRole = useUpdateUserRole();
  const deleteUser = useDeleteUser();

  const [showForm, setShowForm] = useState(false);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<string>("editor");
  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<{
    id: string;
    name: string;
  } | null>(null);

  function handleInvite(e: FormEvent) {
    e.preventDefault();
    setError("");
    createUser.mutate(
      { email, password, full_name: fullName, role },
      {
        onSuccess: () => {
          setShowForm(false);
          setEmail("");
          setFullName("");
          setPassword("");
          setRole("editor");
        },
        onError: (err: unknown) => {
          const detail = (err as { response?: { data?: { detail?: string } } })
            ?.response?.data?.detail;
          setError(detail || "Failed to create user");
        },
      }
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-display text-text-primary">Team</h1>
          {users && <Badge>{users.length} members</Badge>}
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          {showForm ? (
            <>
              <ChevronUp className="h-4 w-4" strokeWidth={1.5} />
              Cancel
            </>
          ) : (
            <>
              <UserPlus className="h-4 w-4" strokeWidth={1.5} />
              Invite
            </>
          )}
        </Button>
      </div>

      {/* Invite panel */}
      <AnimatePresence>
        {showForm && (
          <motion.form
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            onSubmit={handleInvite}
            className="mt-lg overflow-hidden rounded-lg border border-border bg-surface p-lg space-y-lg"
          >
            {error && (
              <div className="rounded-md bg-danger-subtle p-md text-body text-danger">
                {error}
              </div>
            )}
            <div className="grid grid-cols-1 gap-lg sm:grid-cols-2">
              <Input
                label="Full Name"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Jane Doe"
              />
              <Input
                label="Email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="jane@company.com"
              />
              <Input
                label="Password"
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Min. 6 characters"
              />
              <div className="space-y-1.5">
                <label className="block text-body-medium text-text-primary">
                  Role
                </label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-border bg-surface px-3 py-2 text-body text-text-primary shadow-xs focus-ring"
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r.charAt(0).toUpperCase() + r.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <Button type="submit" loading={createUser.isPending}>
              <UserPlus className="h-4 w-4" strokeWidth={1.5} />
              Create user
            </Button>
          </motion.form>
        )}
      </AnimatePresence>

      {/* Table */}
      {isLoading ? (
        <div className="mt-xl space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded-lg bg-border-subtle" />
          ))}
        </div>
      ) : (
        <div className="mt-xl rounded-lg border border-border overflow-hidden">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-border-subtle bg-surface">
                <th className="px-lg py-md text-left text-caption font-medium uppercase tracking-wider text-text-tertiary">
                  Member
                </th>
                <th className="px-lg py-md text-left text-caption font-medium uppercase tracking-wider text-text-tertiary">
                  Role
                </th>
                <th className="px-lg py-md text-right text-caption font-medium uppercase tracking-wider text-text-tertiary">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {users?.map((u, i) => {
                const isSelf = u.id === currentUser?.user_id;
                return (
                  <motion.tr
                    key={u.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.03 }}
                    className="group border-b border-border-subtle last:border-0 hover:bg-accent-subtle/30 transition-colors"
                  >
                    <td className="px-lg py-md">
                      <div className="flex items-center gap-3">
                        <Avatar name={u.full_name} role={u.role} />
                        <div>
                          <p className="text-body-medium text-text-primary">
                            {u.full_name}
                            {isSelf && (
                              <span className="ml-1.5 text-caption text-text-tertiary">
                                (you)
                              </span>
                            )}
                          </p>
                          <p className="text-caption text-text-tertiary">
                            {u.email}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-lg py-md">
                      {isSelf ? (
                        <Badge
                          variant={u.role as "admin" | "editor" | "viewer"}
                          dot
                        >
                          {u.role}
                        </Badge>
                      ) : (
                        <select
                          value={u.role}
                          onChange={(e) =>
                            updateRole.mutate({
                              id: u.id,
                              role: e.target.value,
                            })
                          }
                          className="rounded-md border border-border bg-surface px-2.5 py-1 text-caption text-text-primary focus-ring"
                        >
                          {ROLES.map((r) => (
                            <option key={r} value={r}>
                              {r}
                            </option>
                          ))}
                        </select>
                      )}
                    </td>
                    <td className="px-lg py-md text-right">
                      {!isSelf && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            setDeleteTarget({ id: u.id, name: u.full_name })
                          }
                          className="text-text-tertiary hover:text-danger opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <Trash2 className="h-4 w-4" strokeWidth={1.5} />
                        </Button>
                      )}
                    </td>
                  </motion.tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete dialog */}
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Remove team member"
        description={`Remove ${deleteTarget?.name} from your team? They will lose access immediately.`}
        confirmLabel="Remove"
        variant="danger"
        loading={deleteUser.isPending}
        onConfirm={() => {
          if (deleteTarget) {
            deleteUser.mutate(deleteTarget.id, {
              onSuccess: () => setDeleteTarget(null),
            });
          }
        }}
      />
    </div>
  );
}
