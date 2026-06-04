"use client";

import { useEffect, useState } from "react";
import { api, TierInfo } from "@/lib/api";
import { CreditCard, Check, Crown, Zap, Star } from "lucide-react";

const tierIcons: any = {
  Free: Zap,
  Starter: Star,
  Pro: Crown,
  Enterprise: CreditCard,
};

export default function BillingPage() {
  const [tiers, setTiers] = useState<TierInfo[]>([]);
  const [subscription, setSubscription] = useState<any>(null);

  useEffect(() => {
    api.getTiers().then(setTiers);
    api.getSubscription().then(setSubscription).catch(() => {});
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Billing</h1>

      {/* Current Plan */}
      {subscription && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-2">Current Plan</h2>
          <div className="flex items-center gap-3">
            <span className="text-2xl font-bold capitalize text-emerald-400">
              {subscription.tier}
            </span>
            <span
              className={`px-2 py-0.5 rounded text-xs ${
                subscription.status === "active"
                  ? "bg-emerald-500/10 text-emerald-400"
                  : "bg-red-500/10 text-red-400"
              }`}
            >
              {subscription.status}
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            {subscription.requests_per_day === -1
              ? "Unlimited requests"
              : `${subscription.requests_per_day.toLocaleString()} requests/day`}
          </p>
          {subscription.cancel_at_period_end && (
            <p className="text-sm text-yellow-400 mt-2">
              Cancels at end of billing period
            </p>
          )}
        </div>
      )}

      {/* Pricing Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {tiers.map((tier) => {
          const Icon = tierIcons[tier.name] || Zap;
          const isCurrent = subscription?.tier === tier.name.toLowerCase();

          return (
            <div
              key={tier.name}
              className={`bg-gray-900 border rounded-xl p-6 ${
                isCurrent ? "border-emerald-500" : "border-gray-800"
              }`}
            >
              {isCurrent && (
                <div className="text-xs text-emerald-400 font-medium mb-3">
                  CURRENT PLAN
                </div>
              )}
              <div className="flex items-center gap-2 mb-3">
                <Icon className="w-5 h-5 text-gray-400" />
                <h3 className="text-lg font-semibold">{tier.name}</h3>
              </div>
              <div className="mb-4">
                <span className="text-3xl font-bold">${tier.price}</span>
                {tier.price > 0 && (
                  <span className="text-gray-400 text-sm">/month</span>
                )}
              </div>
              <div className="text-sm text-gray-400 mb-4">
                {tier.requests_per_day === -1
                  ? "Unlimited requests"
                  : `${tier.requests_per_day.toLocaleString()} req/day`}
              </div>
              <ul className="space-y-2 mb-6">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2 text-sm">
                    <Check className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
                    <span className="text-gray-300">{feature}</span>
                  </li>
                ))}
              </ul>
              {!isCurrent && tier.price > 0 && (
                <button className="w-full bg-emerald-600 hover:bg-emerald-700 py-2 rounded-lg text-sm font-medium transition-colors">
                  Upgrade
                </button>
              )}
              {isCurrent && (
                <button
                  disabled
                  className="w-full bg-gray-800 text-gray-500 py-2 rounded-lg text-sm"
                >
                  Current Plan
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
