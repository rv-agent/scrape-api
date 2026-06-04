"use client";

import { useEffect, useState } from "react";
import { api, UsageStats } from "@/lib/api";
import {
  Activity,
  Zap,
  Clock,
  TrendingUp,
  AlertCircle,
  CheckCircle,
} from "lucide-react";

function StatCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: string | number;
  icon: any;
  color: string;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-400">{label}</p>
          <p className="text-2xl font-bold text-white mt-1">{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [health, setHealth] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const key = localStorage.getItem("api_key");
    if (!key) {
      setError("Set your API key in localStorage: localStorage.setItem('api_key', 'your-key')");
      return;
    }

    api.getUsage().then(setStats).catch((e) => setError(e.message));
    api.health().then(setHealth).catch(() => {});
  }, []);

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-400" />
          <div>
            <p className="text-red-400 font-medium">Connection Error</p>
            <p className="text-sm text-gray-400 mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div className="flex items-center gap-2 text-sm">
          {health ? (
            <span className="flex items-center gap-1.5 text-emerald-400">
              <CheckCircle className="w-4 h-4" />
              API Healthy
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-gray-500">
              <Clock className="w-4 h-4" />
              Checking...
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Requests Today"
          value={stats?.requests_today ?? "—"}
          icon={Zap}
          color="bg-emerald-500/10 text-emerald-400"
        />
        <StatCard
          label="Monthly Requests"
          value={stats?.requests_this_month?.toLocaleString() ?? "—"}
          icon={TrendingUp}
          color="bg-blue-500/10 text-blue-400"
        />
        <StatCard
          label="Total Requests"
          value={stats?.total_requests?.toLocaleString() ?? "—"}
          icon={Activity}
          color="bg-purple-500/10 text-purple-400"
        />
        <StatCard
          label="Avg Response"
          value={stats ? `${Math.round(stats.avg_response_time_ms)}ms` : "—"}
          icon={Clock}
          color="bg-orange-500/10 text-orange-400"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-4">API Key Info</h2>
          {stats ? (
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">Key</span>
                <span className="font-mono text-sm">{stats.key_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Tier</span>
                <span className="capitalize px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded text-sm">
                  {stats.tier}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Limit</span>
                <span>{stats.requests_limit.toLocaleString()}</span>
              </div>
              <div className="mt-4">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-400">Usage</span>
                  <span>{Math.round((stats.requests_today / stats.requests_limit) * 100)}%</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-2">
                  <div
                    className="bg-emerald-500 h-2 rounded-full transition-all"
                    style={{
                      width: `${Math.min((stats.requests_today / stats.requests_limit) * 100, 100)}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          ) : (
            <p className="text-gray-500">Loading...</p>
          )}
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-4">Quick Start</h2>
          <div className="space-y-3 text-sm">
            <div className="bg-gray-800 rounded-lg p-3 font-mono text-xs overflow-x-auto">
              <p className="text-gray-500"># Scrape a URL</p>
              <p className="text-emerald-400">curl -X POST http://localhost:8000/api/v1/scrape \</p>
              <p className="text-yellow-300">  -H "X-API-Key: YOUR_KEY" \</p>
              <p className="text-yellow-300">  -H "Content-Type: application/json" \</p>
              <p className="text-yellow-300">  -d {"'"}{"{"}"url": "https://example.com"{"}"  }{"'"}</p>
            </div>
            <p className="text-gray-400">
              Check the{" "}
              <a href="/docs" className="text-emerald-400 hover:underline">
                API Docs
              </a>{" "}
              for all endpoints.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
