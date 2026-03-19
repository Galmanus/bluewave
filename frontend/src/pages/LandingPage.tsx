import { useAuth } from "../contexts/AuthContext";
import Hero from "../components/landing/Hero";
import PainPoints from "../components/landing/PainPoints";
import Features from "../components/landing/Features";
import SocialProof from "../components/landing/SocialProof";
import Pricing from "../components/landing/Pricing";
import HowItWorks from "../components/landing/HowItWorks";
import Comparison from "../components/landing/Comparison";
import FAQ from "../components/landing/FAQ";
import FinalCTA from "../components/landing/FinalCTA";
import Footer from "../components/landing/Footer";

export default function LandingPage() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return null;

  return (
    <>
      <Hero isAuthenticated={isAuthenticated} />
      <PainPoints />
      <Features />
      <SocialProof />
      <Pricing isAuthenticated={isAuthenticated} />
      <HowItWorks />
      <Comparison />
      <FAQ />
      <FinalCTA isAuthenticated={isAuthenticated} />
      <Footer />
    </>
  );
}
