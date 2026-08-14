// epiSTEMic AI feedback proxy.
//
// Keeps the Gemini API key server-side (as a Worker secret) instead of
// embedding it in the public investigation.html, which is served from
// unauthenticated GitHub Pages and readable by anyone.
//
// Deploy via the Cloudflare dashboard (Workers & Pages -> Create -> Quick
// Edit, paste this in, deploy), then add a secret named GEMINI_API_KEY
// under the worker's Settings -> Variables and Secrets. Update ALLOWED_ORIGINS
// below if the site is ever served from a different domain.

const ALLOWED_ORIGINS = [
  "https://mmj125.github.io",
];
const LOCALHOST_ORIGIN = /^http:\/\/localhost:\d+$/;

// Google's free-tier model lineup shifts and old aliases get sunset for new
// API keys without much warning (gemini-2.5-flash 404'd within weeks of this
// being written). If this starts 404ing again, check the current models at
// https://ai.google.dev/gemini-api/docs/models and update this constant.
const GEMINI_MODEL = "gemini-3.5-flash";

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowOrigin = isAllowedOrigin(origin) ? origin : ALLOWED_ORIGINS[0];

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders(allowOrigin) });
    }
    if (request.method !== "POST") {
      return json({ error: "Method not allowed" }, 405, allowOrigin);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: "Invalid JSON body" }, 400, allowOrigin);
    }

    const { systemPrompt, userPrompt } = body || {};
    if (!systemPrompt || !userPrompt) {
      return json({ error: "systemPrompt and userPrompt are required" }, 400, allowOrigin);
    }

    if (!env.GEMINI_API_KEY) {
      console.error("GEMINI_API_KEY secret is missing or empty on this worker");
      return json({ error: "Server is not configured with an API key" }, 500, allowOrigin);
    }

    let geminiResp;
    try {
      geminiResp = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-goog-api-key": env.GEMINI_API_KEY,
          },
          body: JSON.stringify({
            systemInstruction: { parts: [{ text: systemPrompt }] },
            contents: [{ role: "user", parts: [{ text: userPrompt }] }],
            generationConfig: { maxOutputTokens: 1000 },
          }),
        }
      );
    } catch (err) {
      console.error("Fetch to Gemini failed:", err);
      return json({ error: "Could not reach Gemini API", detail: String(err) }, 502, allowOrigin);
    }

    if (!geminiResp.ok) {
      const errText = await geminiResp.text();
      console.error("Gemini API returned", geminiResp.status, errText);
      return json({ error: "Gemini API error", detail: errText }, 502, allowOrigin);
    }

    const data = await geminiResp.json();
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text || "";
    if (!text) {
      console.error("Gemini response had no text:", JSON.stringify(data));
      return json({ error: "No feedback returned", detail: data }, 502, allowOrigin);
    }

    return json({ text }, 200, allowOrigin);
  },
};

function isAllowedOrigin(origin) {
  return ALLOWED_ORIGINS.includes(origin) || LOCALHOST_ORIGIN.test(origin);
}

function corsHeaders(allowOrigin) {
  return {
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function json(obj, status, allowOrigin) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders(allowOrigin) },
  });
}
