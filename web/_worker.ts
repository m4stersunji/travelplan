// Static-assets-only Worker. Serves built SPA from `dist/`.
// Falls back to index.html for client-side routes.
interface Env {
  ASSETS: { fetch: (req: Request) => Promise<Response> };
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    // Try the asset directly
    const direct = await env.ASSETS.fetch(request);
    if (direct.status !== 404) return direct;
    // SPA fallback to index.html for non-asset paths
    if (!url.pathname.includes(".")) {
      const indexReq = new Request(new URL("/", request.url), request);
      return env.ASSETS.fetch(indexReq);
    }
    return direct;
  },
};
