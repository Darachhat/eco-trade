import React from 'react';
import { useModelStore } from '../stores/useModelStore';
import { ModelCard } from '../components/models/ModelCard';
import { RegimeIndicator } from '../components/models/RegimeIndicator';
import { SHAPWaterfall } from '../components/signals/SHAPWaterfall';
import { SHAP_CONTRIBUTIONS } from '../lib/quant/engine';
import { Cpu, Award, Activity, Sliders } from 'lucide-react';

export const AiIntelligenceView: React.FC = () => {
  const models = useModelStore((s) => s.models);
  const regime = useModelStore((s) => s.regime);
  const selectedModelId = useModelStore((s) => s.selectedModelId);
  const setSelectedModelId = useModelStore((s) => s.setSelectedModelId);

  const selectedModel = models.find((m) => m.id === selectedModelId) || models[0];

  return (
    <div className="space-y-4 p-3 font-mono">
      {/* 1. Header Banner */}
      <div className="terminal-panel p-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Cpu className="w-5 h-5 text-terminal-cyan" />
          <div>
            <h1 className="text-sm font-bold text-terminal-text uppercase tracking-wider">
              AI Quantitative Intelligence & Model Architecture
            </h1>
            <p className="text-2xs text-terminal-muted">
              10 Multi-Model Ensemble, Real-Time Regime Detection, and Feature Explainability
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-2xs text-terminal-muted">
          <Award className="w-4 h-4 text-terminal-cyan" />
          <span>Active Champion: <strong className="text-terminal-cyan">Transformer Alpha v18</strong></span>
        </div>
      </div>

      {/* 2. Market Regime Engine */}
      <RegimeIndicator regime={regime} />

      {/* 3. 10 Quantitative Models Leaderboard Grid */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-2xs uppercase tracking-widest text-terminal-muted font-semibold">
          <span>Ensemble Model Roster (10 Predictive Architectures)</span>
          <span className="text-terminal-cyan">Click a model to inspect hyperparameters</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
          {models.map((model) => (
            <ModelCard
              key={model.id}
              model={model}
              isSelected={model.id === selectedModelId}
              onSelect={setSelectedModelId}
            />
          ))}
        </div>
      </div>

      {/* 4. Model Deep-Dive & Global SHAP Feature Importance */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* Selected Model Detailed Hyperparameters & Regime Performance (5 cols) */}
        <div className="lg:col-span-5 terminal-panel p-3.5 space-y-3">
          <div className="terminal-header -mx-3.5 -mt-3.5 mb-2">
            <span>Model Details: {selectedModel.name}</span>
            <span className="text-terminal-cyan">{selectedModel.version}</span>
          </div>

          <div className="space-y-2 text-xs">
            <div className="text-2xs uppercase tracking-wider text-terminal-muted font-semibold">
              Performance by Market Regime
            </div>
            <div className="grid grid-cols-2 gap-2 text-2xs">
              {Object.entries(selectedModel.regimePerformance).map(([reg, perf]) => (
                <div key={reg} className="p-2 bg-terminal-surface/40 rounded border border-terminal-border/60">
                  <span className="text-terminal-muted block truncate">{reg.replace(/_/g, ' ')}</span>
                  <div className="flex justify-between font-bold mt-1">
                    <span className="text-terminal-bull">Win: {(perf.winRate * 100).toFixed(0)}%</span>
                    <span className="text-terminal-text">PF: {perf.profitFactor.toFixed(2)}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="text-2xs uppercase tracking-wider text-terminal-muted font-semibold pt-2">
              Hyperparameter Specification
            </div>
            <div className="p-2.5 bg-terminal-bg rounded border border-terminal-border text-2xs space-y-1">
              {Object.entries(selectedModel.hyperparameters).map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <span className="text-terminal-muted">{k}:</span>
                  <span className="font-bold text-terminal-text">{String(v)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Global SHAP Feature Importance (7 cols) */}
        <div className="lg:col-span-7 terminal-panel p-3.5 space-y-2">
          <div className="terminal-header -mx-3.5 -mt-3.5 mb-2">
            <span>Global Feature Importance (SHAP Attribution Across All Features)</span>
            <span className="text-terminal-cyan">180 Bars Rolling Window</span>
          </div>
          <SHAPWaterfall contributions={SHAP_CONTRIBUTIONS} />
        </div>
      </div>
    </div>
  );
};
