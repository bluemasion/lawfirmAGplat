import { useState } from 'react';
import GlobalHeader from './components/GlobalHeader';
import Sidebar from './components/Sidebar';
import AICopilot from './components/AICopilot';
import Dashboard from './pages/Dashboard';
import AppCenter from './pages/AppCenter';
import ModelHub from './pages/ModelHub';
import Settings from './pages/Settings';
import SecuritiesAgent from './agents/SecuritiesAgent';
import LegalTranslation from './agents/LegalTranslation';
import ConflictSearch from './agents/ConflictSearch';
import BiddingAgent from './agents/BiddingAgent';

const agentComponents = {
  securities: SecuritiesAgent,
  translation: LegalTranslation,
  conflict: ConflictSearch,
  bidding: BiddingAgent,
};

export default function App() {
  const [activeTab, setActiveTab] = useState('workbench');
  const [activeAgent, setActiveAgent] = useState(null);
  const [testModel, setTestModel] = useState(null);

  const handleSelectAgent = (id) => setActiveAgent(id);
  const handleBack = () => setActiveAgent(null);
  const handleReset = () => { setActiveTab('workbench'); setActiveAgent(null); setTestModel(null); };

  const renderContent = () => {
    if (activeAgent) {
      const AgentComp = agentComponents[activeAgent];
      return AgentComp ? <AgentComp onBack={handleBack} /> : null;
    }
    if (testModel) {
      return (
        <div className="p-6 animate-in">
          <button onClick={() => setTestModel(null)} className="text-zinc-400 hover:text-zinc-700 text-sm mb-4">← Back to Instance Hub</button>
          <div className="bg-[#0d1117] rounded-sm p-6 h-[500px] font-mono text-emerald-400 text-[11px] shadow-inner border border-zinc-700">
            <p className="text-zinc-500">Connected to: {testModel.name}</p>
            <p className="text-zinc-500">Provider: {testModel.provider}</p>
            <p className="text-zinc-500 mb-4">─────────────────────────────────</p>
            <p>{'>'} Model ready. Type your prompt below.</p>
            <p className="mt-2 animate-pulse">▌</p>
          </div>
        </div>
      );
    }
    switch (activeTab) {
      case 'workbench': return <Dashboard />;
      case 'appcenter': return <AppCenter onSelectAgent={handleSelectAgent} />;
      case 'modelhub': return <ModelHub onSelectTest={setTestModel} />;
      case 'settings': return <Settings />;
      default: return <Dashboard />;
    }
  };

  return (
    <div className="h-screen flex flex-col bg-[#f4f5f7] text-zinc-900">
      <GlobalHeader onReset={handleReset} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar activeTab={activeTab} activeAgent={activeAgent} testModel={testModel} onSelectTab={(id) => { setActiveTab(id); setActiveAgent(null); setTestModel(null); }} />
        <main className="flex-1 overflow-y-auto bg-[#f4f5f7]">
          {renderContent()}
        </main>
      </div>
      <AICopilot />
    </div>
  );
}
