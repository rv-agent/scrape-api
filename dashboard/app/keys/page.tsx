"use client";

import { useEffect, useState } from "react";
import { api, APIKey } from "@/lib/api";
import { Plus, Trash2, Copy, Key, Check } from "lucide-react";

export default function KeysPage() {
  const [keys, setKeys] = useState<APIKey[]>([]);
  const [newName, setNewName] = useState("");
  const [newTier, setNewTier] = useState("free");
  const [createdKey, setCreatedKey] = useState("");
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadKeys = () => {
    api.listKeys().then(setKeys).finally(() => setLoading(false));
  };

  useEffect(() => { loadKeys(); }, []);

  const handleCreate = async () => {
    if (!newName) return;
    const res = await api.createKey(newName, newTier);
    setCreatedKey(res.key);
    setNewName("");
    loadKeys();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this API key?")) return;
    await api.deleteKey(id);
    loadKeys();
  };

  const handleCopy = (key: string) => {
    navigator.clipboard.writeText(key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">API Keys</h1>

      {/* Create */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold mb-4">Create New Key</h2>
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="Key name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-emerald-500"
          />
          <select
            value={newTier}
            onChange={(e) => setNewTier(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none"
          >
            <option value="free">Free</option>
            <option value="starter">Starter</option>
            <option value="pro">Pro</option>
            <option value="enterprise">Enterprise</option>
          </select>
          <button
            onClick={handleCreate}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create
          </button>
        </div>

        {createdKey && (
          <div className="mt-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-4 flex items-center justify-between">
            <div>
              <p className="text-sm text-emerald-400 font-medium">Key Created!</p>
              <p className="font-mono text-sm mt-1">{createdKey}</p>
            </div>
            <button
              onClick={() => handleCopy(createdKey)}
              className="flex items-center gap-1.5 text-sm text-emerald-400 hover:text-emerald-300"
            >
              {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
        )}
      </div>

      {/* List */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left p-4 text-sm text-gray-400 font-medium">Name</th>
              <th className="text-left p-4 text-sm text-gray-400 font-medium">Key</th>
              <th className="text-left p-4 text-sm text-gray-400 font-medium">Tier</th>
              <th className="text-left p-4 text-sm text-gray-400 font-medium">Usage</th>
              <th className="text-left p-4 text-sm text-gray-400 font-medium">Status</th>
              <th className="text-right p-4 text-sm text-gray-400 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {keys.map((key) => (
              <tr key={key.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="p-4 text-sm">{key.name}</td>
                <td className="p-4 font-mono text-sm text-gray-400">{key.key_prefix}...</td>
                <td className="p-4">
                  <span className="capitalize px-2 py-0.5 bg-gray-800 rounded text-xs">
                    {key.tier}
                  </span>
                </td>
                <td className="p-4 text-sm">
                  {key.requests_today} / {key.requests_limit}
                </td>
                <td className="p-4">
                  <span
                    className={`inline-flex items-center gap-1 text-xs ${
                      key.is_active ? "text-emerald-400" : "text-red-400"
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        key.is_active ? "bg-emerald-400" : "bg-red-400"
                      }`}
                    />
                    {key.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="p-4 text-right">
                  <button
                    onClick={() => handleDelete(key.id)}
                    className="text-gray-500 hover:text-red-400 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
            {keys.length === 0 && !loading && (
              <tr>
                <td colSpan={6} className="p-8 text-center text-gray-500">
                  No API keys yet. Create one above.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
