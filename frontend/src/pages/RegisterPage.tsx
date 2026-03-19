import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Waves } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [tenantName, setTenantName] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const strength =
    password.length === 0
      ? 0
      : password.length < 6
        ? 1
        : password.length < 10
          ? 2
          : 3;
  const strengthColor = ["", "bg-danger", "bg-warning", "bg-success"];
  const strengthLabel = ["", "Weak", "Fair", "Strong"];

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(tenantName, email, password, fullName);
      navigate("/");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      setError(detail || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-lg">
      <div className="absolute inset-0 bg-gradient-to-br from-accent-subtle via-background to-background" />
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
        className="relative z-10 w-full max-w-sm space-y-xl rounded-xl border border-border bg-surface p-2xl shadow-lg"
      >
        <div className="flex flex-col items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-subtle">
            <Waves className="h-5 w-5 text-accent" />
          </div>
          <div className="text-center">
            <h1 className="text-heading text-text-primary">Create your team</h1>
            <p className="mt-1 text-body text-text-secondary">
              You'll be the admin of your new workspace
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-lg">
          {error && (
            <div className="rounded-md bg-danger-subtle p-md text-body text-danger">
              {error}
            </div>
          )}
          <Input
            label="Team / Company Name"
            required
            value={tenantName}
            onChange={(e) => setTenantName(e.target.value)}
            placeholder="Acme Agency"
          />
          <Input
            label="Your Full Name"
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
            placeholder="you@company.com"
          />
          <div>
            <Input
              label="Password"
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Min. 6 characters"
            />
            {password.length > 0 && (
              <div className="mt-2 flex items-center gap-2">
                <div className="flex flex-1 gap-1">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className={`h-1 flex-1 rounded-full transition-colors ${
                        i <= strength ? strengthColor[strength] : "bg-border"
                      }`}
                    />
                  ))}
                </div>
                <span className="text-caption text-text-tertiary">
                  {strengthLabel[strength]}
                </span>
              </div>
            )}
          </div>
          <Button type="submit" loading={loading} className="w-full">
            Create account
          </Button>
        </form>

        <p className="text-center text-body text-text-secondary">
          Already have an account?{" "}
          <Link
            to="/login"
            className="font-medium text-accent hover:text-accent-hover"
          >
            Sign in
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
