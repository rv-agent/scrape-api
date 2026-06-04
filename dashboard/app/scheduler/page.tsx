"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Plus, Trash2, Clock, Play, Pause } from "lucide-react";

export default function SchedulerPage() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [interval, setInterval] = useState("3600");
  const [loading, setLoading] = useState(true);

  const load = () => {
    api.listScheduledJobs().then(setJobs).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!name || !url) return;
    await api.createScheduledJob({
      name,
      url,
      interval_seconds: parseInt(interval),
    });
    setName("");
    setUrl("");
    load();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this scheduled job?")) return;
    await api.deleteScheduledJob(id);
    load();
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Scheduler</h1>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold mb-4">Schedule New Job</h2>
        <div className="space-y-3">
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="Job name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-emerald-500"
            />
            <input
              type="url"
              placeholder="https://example.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-emerald-500"
            />
          </div>
          <div className="flex gap-3">
            <select
              value={interval}
              onChange={(e) => setInterval(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none"
            >
              <option value="300">Every 5 minutes</option>
              <option value="900">Every 15 minutes</option>
              <option value="3600">Every hour</option>
              <option value="21600">Every 6 hours</option>
              <option value="86400">Daily</option>
            </select>
            <button
              onClick={handleCreate}
              className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 px-4 py-2 rounded-lg text-sm font-medium"
            >
              <Plus className="w-4 h-4" />
              Schedule
            </button>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {jobs.map((job) => (
          <div key={job.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm font-medium">{job.name}</p>
                <p className="text-xs text-gray-500 font-mono">{job.url}</p>
                <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                  <span>
                    {job.cron_expression || `Every ${job.interval_seconds}s`}
                  </span>
                  <span>Runs: {job.run_count}</span>
                  <span
                    className={`flex items-center gap-1 ${
                      job.is_active ? "text-emerald-400" : "text-gray-500"
                    }`}
                  >
                    {job.is_active ? (
                      <Play className="w-3 h-3" />
                    ) : (
                      <Pause className="w-3 h-3" />
                    )}
                    {job.is_active ? "Active" : "Paused"}
                  </span>
                </div>
              </div>
            </div>
            <button
              onClick={() => handleDelete(job.id)}
              className="text-gray-500 hover:text-red-400"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        ))}
        {jobs.length === 0 && !loading && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center text-gray-500">
            No scheduled jobs.
          </div>
        )}
      </div>
    </div>
  );
}
