/**
 * Traakeer Streams SDK — Behavioral signal capture for real-time PUT psychometrics.
 *
 * Captures: mouse trajectory, keystroke dynamics, scroll patterns,
 * gaze proxy (mouse as attention proxy), hesitation events, heartbeat.
 *
 * Sends aggregated heartbeats every HEARTBEAT_MS via WebSocket.
 * Falls back to POST /streams/event if WebSocket unavailable.
 */

export interface MouseMetrics {
  velocity_avg: number;       // px/ms average
  velocity_max: number;       // peak velocity
  acceleration_avg: number;   // px/ms^2
  hesitation_count: number;   // times velocity dropped near-zero
  hesitation_ms_total: number; // total ms spent in hesitation zones
  jitter: number;             // variance in direction changes (0–1)
  click_count: number;
  click_force_avg: number;    // always 1 for mouse, touch pressure if available
}

export interface ScrollMetrics {
  speed_avg: number;          // px/ms
  speed_max: number;
  reversal_count: number;     // scroll direction reversals (re-reads)
  dwell_ms_total: number;     // time without scrolling
  total_distance_px: number;
  direction_bias: number;     // -1 up-heavy, +1 down-heavy
}

export interface KeystrokeMetrics {
  key_count: number;
  deletion_count: number;
  deletion_rate: number;      // deletions / total keys
  iki_avg_ms: number;         // inter-key interval average
  iki_variance: number;       // IKI variance — high = stressed/unsure
  burst_count: number;        // typing bursts (rapid sequences)
  pause_before_submit_ms: number; // last pause before Enter/Tab
  wpm_estimate: number;
}

export interface GazeProxy {
  // Mouse position as proxy for visual attention
  center_x: number;           // normalized 0–1
  center_y: number;
  variance_x: number;
  variance_y: number;
  quadrant_dwell: [number, number, number, number]; // TL, TR, BL, BR ms
  element_focus?: string;     // last element hovered (tag#id.class)
}

export interface Heartbeat {
  session_id: string;
  user_id?: string;
  page: string;
  ts: number;
  interval_ms: number;
  mouse: MouseMetrics;
  scroll: ScrollMetrics;
  keystrokes: KeystrokeMetrics;
  gaze_proxy: GazeProxy;
  event_count: number;        // raw events captured this interval
}

// ── Config ──────────────────────────────────────────────────────────────────

const HEARTBEAT_MS = 1000;          // emit P(t) update every second
const HESITATION_THRESHOLD_PX_MS = 0.05; // velocity below this = hesitation
const BURST_IKI_THRESHOLD_MS = 120; // IKI below this = typing burst

// ── State accumulators ──────────────────────────────────────────────────────

interface RawState {
  // Mouse
  mouse_positions: Array<{ x: number; y: number; t: number }>;
  click_count: number;
  click_forces: number[];

  // Scroll
  scroll_positions: Array<{ y: number; t: number }>;
  last_scroll_y: number;
  last_scroll_t: number;
  scroll_dwell_start: number;

  // Keystrokes
  key_timestamps: number[];
  deletion_count: number;
  total_keys: number;
  last_key_t: number;
  last_was_enter: boolean;
  pause_before_submit_ms: number;

  // Gaze proxy
  gaze_samples: Array<{ x: number; y: number; t: number }>;

  // General
  event_count: number;
  interval_start: number;
}

function freshState(): RawState {
  return {
    mouse_positions: [],
    click_count: 0,
    click_forces: [],
    scroll_positions: [],
    last_scroll_y: window.scrollY,
    last_scroll_t: Date.now(),
    scroll_dwell_start: Date.now(),
    key_timestamps: [],
    deletion_count: 0,
    total_keys: 0,
    last_key_t: 0,
    last_was_enter: false,
    pause_before_submit_ms: 0,
    gaze_samples: [],
    event_count: 0,
    interval_start: Date.now(),
  };
}

// ── Extractor functions ──────────────────────────────────────────────────────

function extractMouse(state: RawState): MouseMetrics {
  const pts = state.mouse_positions;
  if (pts.length < 2) {
    return {
      velocity_avg: 0, velocity_max: 0, acceleration_avg: 0,
      hesitation_count: 0, hesitation_ms_total: 0, jitter: 0,
      click_count: state.click_count,
      click_force_avg: state.click_forces.length
        ? state.click_forces.reduce((a, b) => a + b, 0) / state.click_forces.length
        : 0,
    };
  }

  const velocities: number[] = [];
  const directions: number[] = [];
  let hesitation_count = 0;
  let hesitation_ms_total = 0;
  let in_hesitation = false;
  let hesitation_start = 0;

  for (let i = 1; i < pts.length; i++) {
    const dx = pts[i].x - pts[i - 1].x;
    const dy = pts[i].y - pts[i - 1].y;
    const dt = pts[i].t - pts[i - 1].t;
    if (dt <= 0) continue;

    const dist = Math.sqrt(dx * dx + dy * dy);
    const vel = dist / dt;
    velocities.push(vel);
    directions.push(Math.atan2(dy, dx));

    if (vel < HESITATION_THRESHOLD_PX_MS) {
      if (!in_hesitation) {
        in_hesitation = true;
        hesitation_start = pts[i - 1].t;
      }
    } else {
      if (in_hesitation) {
        in_hesitation = false;
        hesitation_count++;
        hesitation_ms_total += pts[i].t - hesitation_start;
      }
    }
  }

  if (in_hesitation && pts.length > 0) {
    hesitation_ms_total += pts[pts.length - 1].t - hesitation_start;
    hesitation_count++;
  }

  const velocity_avg = velocities.length
    ? velocities.reduce((a, b) => a + b, 0) / velocities.length
    : 0;
  const velocity_max = velocities.length ? Math.max(...velocities) : 0;

  // Acceleration
  const accelerations: number[] = [];
  for (let i = 1; i < velocities.length; i++) {
    const dt = (pts[i + 1]?.t ?? pts[i].t) - pts[i].t;
    if (dt > 0) accelerations.push(Math.abs(velocities[i] - velocities[i - 1]) / dt);
  }
  const acceleration_avg = accelerations.length
    ? accelerations.reduce((a, b) => a + b, 0) / accelerations.length
    : 0;

  // Jitter — direction change variance
  let direction_changes = 0;
  for (let i = 1; i < directions.length; i++) {
    let delta = Math.abs(directions[i] - directions[i - 1]);
    if (delta > Math.PI) delta = 2 * Math.PI - delta;
    if (delta > Math.PI / 4) direction_changes++;
  }
  const jitter = directions.length > 1 ? direction_changes / (directions.length - 1) : 0;

  return {
    velocity_avg,
    velocity_max,
    acceleration_avg,
    hesitation_count,
    hesitation_ms_total,
    jitter,
    click_count: state.click_count,
    click_force_avg: state.click_forces.length
      ? state.click_forces.reduce((a, b) => a + b, 0) / state.click_forces.length
      : 0,
  };
}

function extractScroll(state: RawState): ScrollMetrics {
  const pts = state.scroll_positions;
  if (pts.length < 2) {
    return {
      speed_avg: 0, speed_max: 0, reversal_count: 0,
      dwell_ms_total: 0, total_distance_px: 0, direction_bias: 0,
    };
  }

  const speeds: number[] = [];
  let reversal_count = 0;
  let total_distance_px = 0;
  let prev_direction = 0;
  let down_ms = 0;
  let up_ms = 0;
  const now = Date.now();
  const dwell_ms_total = now - state.scroll_dwell_start;

  for (let i = 1; i < pts.length; i++) {
    const dy = pts[i].y - pts[i - 1].y;
    const dt = pts[i].t - pts[i - 1].t;
    if (dt <= 0) continue;

    const dist = Math.abs(dy);
    const speed = dist / dt;
    speeds.push(speed);
    total_distance_px += dist;

    const dir = Math.sign(dy);
    if (dir !== 0) {
      if (dt > 0) {
        if (dir > 0) down_ms += dt;
        else up_ms += dt;
      }
      if (prev_direction !== 0 && dir !== prev_direction) reversal_count++;
      prev_direction = dir;
    }
  }

  const total_time = down_ms + up_ms || 1;
  const direction_bias = (down_ms - up_ms) / total_time;

  return {
    speed_avg: speeds.length ? speeds.reduce((a, b) => a + b, 0) / speeds.length : 0,
    speed_max: speeds.length ? Math.max(...speeds) : 0,
    reversal_count,
    dwell_ms_total,
    total_distance_px,
    direction_bias,
  };
}

function extractKeystrokes(state: RawState): KeystrokeMetrics {
  const ts = state.key_timestamps;
  if (ts.length === 0) {
    return {
      key_count: 0, deletion_count: 0, deletion_rate: 0,
      iki_avg_ms: 0, iki_variance: 0, burst_count: 0,
      pause_before_submit_ms: state.pause_before_submit_ms,
      wpm_estimate: 0,
    };
  }

  const ikis: number[] = [];
  let burst_count = 0;
  let in_burst = false;

  for (let i = 1; i < ts.length; i++) {
    const iki = ts[i] - ts[i - 1];
    ikis.push(iki);
    if (iki < BURST_IKI_THRESHOLD_MS) {
      if (!in_burst) { in_burst = true; burst_count++; }
    } else {
      in_burst = false;
    }
  }

  const iki_avg_ms = ikis.length ? ikis.reduce((a, b) => a + b, 0) / ikis.length : 0;
  const iki_variance = ikis.length > 1
    ? ikis.reduce((acc, v) => acc + Math.pow(v - iki_avg_ms, 2), 0) / ikis.length
    : 0;

  const elapsed_min = (ts[ts.length - 1] - ts[0]) / 60000 || 1 / 60;
  const wpm_estimate = (state.total_keys / 5) / elapsed_min;
  const deletion_rate = state.total_keys > 0 ? state.deletion_count / state.total_keys : 0;

  return {
    key_count: state.total_keys,
    deletion_count: state.deletion_count,
    deletion_rate,
    iki_avg_ms,
    iki_variance,
    burst_count,
    pause_before_submit_ms: state.pause_before_submit_ms,
    wpm_estimate,
  };
}

function extractGaze(state: RawState): GazeProxy {
  const samples = state.gaze_samples;
  if (samples.length === 0) {
    return {
      center_x: 0.5, center_y: 0.5,
      variance_x: 0, variance_y: 0,
      quadrant_dwell: [0, 0, 0, 0],
    };
  }

  const W = window.innerWidth || 1;
  const H = window.innerHeight || 1;

  const xs = samples.map(s => s.x / W);
  const ys = samples.map(s => s.y / H);

  const cx = xs.reduce((a, b) => a + b, 0) / xs.length;
  const cy = ys.reduce((a, b) => a + b, 0) / ys.length;
  const vx = xs.reduce((a, v) => a + Math.pow(v - cx, 2), 0) / xs.length;
  const vy = ys.reduce((a, v) => a + Math.pow(v - cy, 2), 0) / ys.length;

  // Quadrant dwell (time estimate via sample count)
  const q: [number, number, number, number] = [0, 0, 0, 0];
  for (let i = 1; i < samples.length; i++) {
    const dt = samples[i].t - samples[i - 1].t;
    const nx = samples[i].x / W;
    const ny = samples[i].y / H;
    if (nx < 0.5 && ny < 0.5) q[0] += dt;
    else if (nx >= 0.5 && ny < 0.5) q[1] += dt;
    else if (nx < 0.5 && ny >= 0.5) q[2] += dt;
    else q[3] += dt;
  }

  return {
    center_x: cx, center_y: cy,
    variance_x: vx, variance_y: vy,
    quadrant_dwell: q,
  };
}

// ── SDK class ──────────────────────────────────────────────────────────────

export class TraakeerStreams {
  private session_id: string;
  private user_id?: string;
  private api_base: string;
  private ws: WebSocket | null = null;
  private ws_ready = false;
  private state: RawState;
  private ticker: ReturnType<typeof setInterval> | null = null;
  private bound_handlers: Array<{ el: EventTarget; type: string; fn: EventListener }> = [];
  private throttle_ms = 16; // ~60fps mouse capture
  private last_mouse_t = 0;

  constructor(opts: {
    session_id: string;
    user_id?: string;
    api_base?: string;
  }) {
    this.session_id = opts.session_id;
    this.user_id = opts.user_id;
    this.api_base = opts.api_base ?? `${window.location.protocol}//${window.location.hostname}:8300`;
    this.state = freshState();
  }

  // ── Public API ────────────────────────────────────────────────────────────

  start() {
    this._connect_ws();
    this._bind_events();
    this.ticker = setInterval(() => this._emit_heartbeat(), HEARTBEAT_MS);
    return this;
  }

  stop() {
    if (this.ticker) clearInterval(this.ticker);
    this.bound_handlers.forEach(({ el, type, fn }) => el.removeEventListener(type, fn));
    this.bound_handlers = [];
    if (this.ws) this.ws.close();
    this.ws = null;
  }

  // ── WebSocket ─────────────────────────────────────────────────────────────

  private _connect_ws() {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${window.location.hostname}:8300/api/v1/streams/session/${this.session_id}`;
    try {
      this.ws = new WebSocket(url);
      this.ws.onopen = () => { this.ws_ready = true; };
      this.ws.onclose = () => {
        this.ws_ready = false;
        // Reconnect after 3s
        setTimeout(() => this._connect_ws(), 3000);
      };
      this.ws.onerror = () => { this.ws_ready = false; };
    } catch {
      this.ws_ready = false;
    }
  }

  // ── Event binding ─────────────────────────────────────────────────────────

  private _bind(el: EventTarget, type: string, fn: EventListener, opts?: AddEventListenerOptions) {
    el.addEventListener(type, fn, opts);
    this.bound_handlers.push({ el, type, fn });
  }

  private _bind_events() {
    const doc = document as EventTarget;
    const win = window as unknown as EventTarget;

    // Mouse move — throttled
    this._bind(doc, "mousemove", (e) => {
      const now = Date.now();
      if (now - this.last_mouse_t < this.throttle_ms) return;
      this.last_mouse_t = now;
      const me = e as MouseEvent;
      this.state.mouse_positions.push({ x: me.clientX, y: me.clientY, t: now });
      this.state.gaze_samples.push({ x: me.clientX, y: me.clientY, t: now });
      this.state.event_count++;
    });

    // Mouse click
    this._bind(doc, "click", (e) => {
      const me = e as MouseEvent;
      this.state.click_count++;
      this.state.click_forces.push(1);
      this.state.event_count++;
    });

    // Touch pressure (mobile)
    this._bind(doc, "touchstart", (e) => {
      const te = e as TouchEvent;
      const force = te.touches[0]?.force ?? 1;
      this.state.click_count++;
      this.state.click_forces.push(force);
      const now = Date.now();
      this.state.mouse_positions.push({ x: te.touches[0].clientX, y: te.touches[0].clientY, t: now });
      this.state.gaze_samples.push({ x: te.touches[0].clientX, y: te.touches[0].clientY, t: now });
      this.state.event_count++;
    }, { passive: true });

    // Scroll
    this._bind(win, "scroll", () => {
      const now = Date.now();
      const y = window.scrollY;
      if (Math.abs(y - this.state.last_scroll_y) > 2) {
        this.state.scroll_positions.push({ y, t: now });
        this.state.last_scroll_y = y;
        this.state.scroll_dwell_start = now; // reset dwell timer on move
      }
      this.state.event_count++;
    }, { passive: true });

    // Keystrokes
    this._bind(doc, "keydown", (e) => {
      const ke = e as KeyboardEvent;
      const now = Date.now();

      if (ke.key === "Backspace" || ke.key === "Delete") {
        this.state.deletion_count++;
      }

      // Capture pause before submit
      if (ke.key === "Enter" || ke.key === "Tab") {
        if (this.state.last_key_t > 0) {
          this.state.pause_before_submit_ms = now - this.state.last_key_t;
        }
      }

      this.state.key_timestamps.push(now);
      this.state.last_key_t = now;
      this.state.total_keys++;
      this.state.event_count++;
    });

    // Visibility — detect tab switches (anxiety signal)
    this._bind(doc, "visibilitychange", () => {
      // Just count as event; extractor will see event_count dip
      this.state.event_count++;
    });
  }

  // ── Heartbeat emission ───────────────────────────────────────────────────

  private _emit_heartbeat() {
    const now = Date.now();
    const interval_ms = now - this.state.interval_start;

    const hb: Heartbeat = {
      session_id: this.session_id,
      user_id: this.user_id,
      page: window.location.pathname,
      ts: now,
      interval_ms,
      mouse: extractMouse(this.state),
      scroll: extractScroll(this.state),
      keystrokes: extractKeystrokes(this.state),
      gaze_proxy: extractGaze(this.state),
      event_count: this.state.event_count,
    };

    this._send(hb);

    // Reset state for next interval
    this.state = freshState();
    this.state.interval_start = now;
  }

  private _send(hb: Heartbeat) {
    const payload = JSON.stringify(hb);

    if (this.ws && this.ws_ready && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(payload);
        return;
      } catch {
        // Fall through to HTTP fallback
      }
    }

    // HTTP fallback
    navigator.sendBeacon
      ? navigator.sendBeacon(`${this.api_base}/api/v1/streams/event`, payload)
      : fetch(`${this.api_base}/api/v1/streams/event`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: payload,
          keepalive: true,
        }).catch(() => {});
  }
}

// ── Convenience factory ──────────────────────────────────────────────────────

let _instance: TraakeerStreams | null = null;

export function initTraakeer(opts: {
  session_id: string;
  user_id?: string;
  api_base?: string;
}): TraakeerStreams {
  if (_instance) _instance.stop();
  _instance = new TraakeerStreams(opts);
  _instance.start();
  return _instance;
}

export function stopTraakeer() {
  if (_instance) { _instance.stop(); _instance = null; }
}
