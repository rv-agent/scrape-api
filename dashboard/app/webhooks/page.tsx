"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Plus, Trash2, Webhook, ExternalLink } from "lucide-react";

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState<any[]>([]);
  const [newUrl, setNewUrl] = useState("");
  const [loading, setLoading] = useState(true);

  const load = () => {
    api.listWebhooks().then(setWebhooks).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!newUrl) return;
    await api.createWebhook(newUrl);
    setNewUrl("");
    load();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this webhook?")) return;
    await api.deleteWebhook(id);
    load();
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Webhooks</h1>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold mb-4">Add Webhook</h2>
        <div className="flex gap-3">
          <input
            type="url"
            placeholder="https://your-server.com/webhook"
            value={newUrl}
            onChange={(e) => setNewUrl(e.target.value)}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-emerald-500"
          />
          <button
            onClick={handleCreate}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 px-4 py-2 rounded-lg text-sm font-medium"
          >
            <Plus className="w-4 h-4" />
            Add
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {webhooks.map((wh) => (
          <div key={wh.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Webhook className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm font-mono">{wh.url}</p>
                <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                  <span>Events: {wh.events}</span>
                  <span
                    className={`flex items-center gap-1 ${
                      wh.is_active ? "text-emerald-400" : "text-red-400"
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        wh.is_active ? "bg-emerald-400" : "bg-red-400"
                      }`}
                    />
                    {wh.is_active ? "Active" : "Inactive"}
                  </span>
                  {wh.failure_count > 0 && (
                    <span className="text-red-400">Failures: {wh.failure_count}</span>
                  )}
                </div>
              </div>
            </div>
            <button
              onClick={() => handleDelete(wh.id)}
              className="text-gray-500 hover:text-red-400"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        ))}
        {webhooks.length === 0 && !loading && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center text-gray-500">
            No webhooks configured.
          </div>
        )}
      </div>
    </div>
  );
}
