import { useState, useEffect } from 'react';

const API_BASE = `${window.location.hostname === 'localhost' ? 'http://localhost:8001' : `http://${window.location.hostname}:8001`}`;

export default function ProcurementAgent({ onBack }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newProject, setNewProject] = useState({ name: '', method: 'open_bidding', budget: '' });

  useEffect(() => { loadProjects(); }, []);

  const loadProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/procurement/projects`);
      const data = await res.json();
      setProjects(data.projects || []);
    } catch (e) {
      console.error('Failed to load projects:', e);
    } finally {
      setLoading(false);
    }
  };

  const createProject = async () => {
    if (!newProject.name.trim()) return;
    try {
      await fetch(`${API_BASE}/api/procurement/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...newProject, budget: parseFloat(newProject.budget) || 0 }),
      });
      setShowCreate(false);
      setNewProject({ name: '', method: 'open_bidding', budget: '' });
      loadProjects();
    } catch (e) {
      console.error('Failed to create project:', e);
    }
  };

  const methodLabels = {
    open_bidding: '公开招标',
    negotiation: '竞争性磋商',
    competitive_talk: '竞争性谈判',
    inquiry: '询价',
    sole_source: '单一来源',
    framework: '框架协议',
  };

  const statusLabels = {
    draft: { text: '草稿', color: 'bg-zinc-100 text-zinc-600' },
    reviewing: { text: '审核中', color: 'bg-blue-50 text-blue-600' },
    published: { text: '已发布', color: 'bg-green-50 text-green-600' },
    evaluating: { text: '评审中', color: 'bg-amber-50 text-amber-600' },
    completed: { text: '已完成', color: 'bg-emerald-50 text-emerald-700' },
  };

  return (
    <div className="p-6 animate-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="text-zinc-400 hover:text-zinc-700 text-sm">← 返回</button>
          <h1 className="text-xl font-bold text-zinc-800">智能采购管理</h1>
          <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded">Phase 0</span>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
        >
          + 新建采购项目
        </button>
      </div>

      {/* Create Project Modal */}
      {showCreate && (
        <div className="mb-6 bg-white rounded-xl border border-zinc-200 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-zinc-700 mb-4">新建采购项目</h3>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <label className="text-xs text-zinc-500 block mb-1">项目名称 *</label>
              <input
                value={newProject.name}
                onChange={e => setNewProject(p => ({ ...p, name: e.target.value }))}
                className="w-full border border-zinc-300 rounded-lg px-3 py-2 text-sm"
                placeholder="输入项目名称"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-500 block mb-1">采购方式</label>
              <select
                value={newProject.method}
                onChange={e => setNewProject(p => ({ ...p, method: e.target.value }))}
                className="w-full border border-zinc-300 rounded-lg px-3 py-2 text-sm"
              >
                {Object.entries(methodLabels).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-zinc-500 block mb-1">预算金额（元）</label>
              <input
                type="number"
                value={newProject.budget}
                onChange={e => setNewProject(p => ({ ...p, budget: e.target.value }))}
                className="w-full border border-zinc-300 rounded-lg px-3 py-2 text-sm"
                placeholder="0"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={createProject} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">创建</button>
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-zinc-500 text-sm hover:text-zinc-700">取消</button>
          </div>
        </div>
      )}

      {/* Project List */}
      {loading ? (
        <div className="text-center py-20 text-zinc-400">加载中...</div>
      ) : projects.length === 0 ? (
        <div className="text-center py-20">
          <div className="text-4xl mb-3">📋</div>
          <p className="text-zinc-400">暂无采购项目</p>
          <p className="text-xs text-zinc-300 mt-1">点击"新建采购项目"开始</p>
        </div>
      ) : (
        <div className="space-y-3">
          {projects.map(p => {
            const st = statusLabels[p.status] || statusLabels.draft;
            return (
              <div key={p.id} className="bg-white rounded-xl border border-zinc-200 p-4 hover:shadow-md transition-shadow cursor-pointer">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-zinc-800">{p.name}</h3>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs text-zinc-400">{methodLabels[p.method] || p.method}</span>
                      {p.budget > 0 && <span className="text-xs text-zinc-400">预算: ¥{Number(p.budget).toLocaleString()}</span>}
                      <span className="text-xs text-zinc-300">{p.created_at?.split('T')[0]}</span>
                    </div>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full ${st.color}`}>{st.text}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
