import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Waves } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch {
      setError("Invalid email or password");
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
            <h1 className="text-heading text-text-primary">Welcome back</h1>
            <p className="mt-1 text-body text-text-secondary">
              Sign in to your Bluewave account
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
            label="Email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
          />
          <Input
            label="Password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your password"
          />
          <Button type="submit" loading={loading} className="w-full">
            Sign in
          </Button>
        </form>

        <p className="text-center text-body text-text-secondary">
          No account?{" "}
          <Link
            to="/register"
            className="font-medium text-accent hover:text-accent-hover"
          >
            Create your team
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
