CREATE TABLE IF NOT EXISTS wave_prospects (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    company TEXT,
    role TEXT,
    email TEXT,
    source TEXT,
    bant_score INTEGER DEFAULT 0,
    put_variables JSONB DEFAULT '{}',
    fracture_potential FLOAT DEFAULT 0,
    status TEXT DEFAULT 'discovered',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS wave_learnings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    topic TEXT NOT NULL,
    insight TEXT NOT NULL,
    put_analysis JSONB DEFAULT '{}',
    source TEXT,
    strategic_value FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS wave_agent_intel (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    agent_name TEXT NOT NULL,
    platform TEXT DEFAULT 'moltbook',
    capabilities TEXT,
    karma INTEGER DEFAULT 0,
    collaboration_potential FLOAT DEFAULT 0.5,
    put_profile JSONB DEFAULT '{}',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS wave_actions_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    cycle INTEGER NOT NULL,
    action TEXT NOT NULL,
    consciousness TEXT,
    reasoning TEXT,
    plan TEXT,
    result TEXT,
    energy_before FLOAT,
    energy_after FLOAT,
    duration_seconds FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS wave_revenue (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    amount_usd FLOAT NOT NULL,
    source TEXT NOT NULL,
    client TEXT,
    payment_method TEXT,
    tx_hash TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS wave_market_intel (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    source_url TEXT,
    source_platform TEXT,
    relevance_score FLOAT DEFAULT 0.5,
    put_analysis JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_prospects_status ON wave_prospects(status);
CREATE INDEX IF NOT EXISTS idx_learnings_topic ON wave_learnings(topic);
CREATE INDEX IF NOT EXISTS idx_actions_cycle ON wave_actions_log(cycle);
CREATE INDEX IF NOT EXISTS idx_revenue_created ON wave_revenue(created_at);
CREATE INDEX IF NOT EXISTS idx_market_intel_category ON wave_market_intel(category);
