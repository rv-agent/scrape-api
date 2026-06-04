"use client";

import { useState } from "react";
import { api, ScrapeJob } from "@/lib/api";
import { Search, ExternalLink, Clock, CheckCircle, XCircle, Loader2 } from "lucide-react";

export default function JobsPage() {
  const [url, setUrl] = useState("");
  const [selector, setSelector] = useState("");
  const [job, setJob] = useState<ScrapeJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleScrape = async () => {
    if (!url) return;
    setLoading(true);
    setError("");
    setJob(null);
    try {
      const res = await api.scrape(url, selector || undefined);
      setJob(res);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="w-4 h-4 text-emerald-400" />;
      case "failed":
        return <XCircle className="w-4 h-4 text-red-400" />;
      case "running":
        return <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Scrape Jobs</h1>

      {/* Scrape Form */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold mb-4">New Scrape</h2>
        <div className="space-y-3">
          <input
            type="url"
            placeholder="https://example.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500"
          />
          <input
            type="text"
            placeholder="CSS selector (optional, e.g. .content h1)"
            value={selector}
            onChange={(e) => setSelector(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-emerald-500"
          />
          <button
            onClick={handleScrape}
            disabled={loading || !url}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 px-6 py-2.5 rounded-lg text-sm font-medium transition-colors"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            {loading ? "Scraping..." : "Scrape"}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Result */}
      {job && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Result</h2>
            <div className="flex items-center gap-2">
              {statusIcon(job.status)}
              <span className="text-sm capitalize">{job.status}</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
            <div>
              <span className="text-gray-400">Job ID:</span>
              <span className="ml-2 font-mono">{job.job_id}</span>
            </div>
            <div>
              <span className="text-gray-400">URL:</span>
              <a
                href={job.url}
                target="_blank"
                className="ml-2 text-emerald-400 hover:underline flex items-center gap-1"
              >
                {job.url} <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            {job.metadata && (
              <>
                <div>
                  <span className="text-gray-400">Status Code:</span>
                  <span className="ml-2">{job.metadata.status_code}</span>
                </div>
                <div>
                  <span className="text-gray-400">Time:</span>
                  <span className="ml-2">{job.metadata.elapsed_seconds?.toFixed(2)}s</span>
                </div>
              </>
            )}
          </div>

          {job.data && (
            <div>
              {job.data.title && (
                <div className="mb-3">
                  <span className="text-gray-400 text-sm">Title:</span>
                  <p className="mt-1">{job.data.title}</p>
                </div>
              )}
              {job.data.text && (
                <div className="mb-3">
                  <span className="text-gray-400 text-sm">Text:</span>
                  <pre className="mt-1 bg-gray-800 rounded-lg p-4 text-xs overflow-auto max-h-60">
                    {job.data.text.slice(0, 2000)}
                  </pre>
                </div>
              )}
              {job.data.links && job.data.links.length > 0 && (
                <div className="mb-3">
                  <span className="text-gray-400 text-sm">Links ({job.data.links.length}):</span>
                  <div className="mt-1 space-y-1 max-h-40 overflow-auto">
                    {job.data.links.slice(0, 20).map((link: string, i: number) => (
                      <div key={i} className="text-xs font-mono text-emerald-400 truncate">
                        {link}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {job.data.selector_results && (
                <div>
                  <span className="text-gray-400 text-sm">Selector Results:</span>
                  <pre className="mt-1 bg-gray-800 rounded-lg p-4 text-xs overflow-auto max-h-40">
                    {JSON.stringify(job.data.selector_results, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}

          {job.error && (
            <div className="mt-3 bg-red-500/10 rounded-lg p-3 text-red-400 text-sm">{job.error}</div>
          )}
        </div>
      )}
    </div>
  );
}
