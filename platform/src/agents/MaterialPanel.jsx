import { useState, useEffect } from 'react';
import { X, Plus, Trash2, Edit3, Users, Briefcase, Award, ArrowLeft, Save, Loader2, ChevronDown, ChevronRight } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const TABS = [
    { key: 'resumes', label: '律师简历', icon: Users, emoji: '👤' },
    { key: 'projects', label: '项目业绩', icon: Briefcase, emoji: '💼' },
    { key: 'qualifications', label: '资质证书', icon: Award, emoji: '🏅' },
];

const RESUME_FIELDS = [
    { key: 'name', label: '姓名', required: true },
    { key: 'title', label: '职位' },
    { key: 'years_of_practice', label: '执业年限' },
    { key: 'specialty', label: '专业方向' },
    { key: 'license_number', label: '执业证号' },
    { key: 'education', label: '学历' },
    { key: 'representative_cases', label: '代表案例', array: true },
    { key: 'brief_bio', label: '简介', multiline: true },
];

const PROJECT_FIELDS = [
    { key: 'project_name', label: '项目名称', required: true },
    { key: 'client', label: '委托方' },
    { key: 'project_type', label: '项目类型' },
    { key: 'contract_amount', label: '合同金额' },
    { key: 'period', label: '服务期间' },
    { key: 'lead_lawyer', label: '项目负责人' },
    { key: 'description', label: '项目描述', multiline: true },
];

const QUAL_FIELDS = [
    { key: 'name', label: '资质名称', required: true },
    { key: 'number', label: '编号' },
    { key: 'issuer', label: '颁发机构' },
    { key: 'valid_until', label: '有效期至' },
];

const FIELD_MAP = {
    resumes: RESUME_FIELDS,
    projects: PROJECT_FIELDS,
    qualifications: QUAL_FIELDS,
};

const KEY_FIELD = {
    resumes: 'name',
    projects: 'project_name',
    qualifications: 'name',
};

export default function MaterialPanel({ onClose }) {
    const [activeTab, setActiveTab] = useState('resumes');
    const [materials, setMaterials] = useState({ resumes: [], projects: [], qualifications: [] });
    const [summary, setSummary] = useState({ resumes: 0, projects: 0, qualifications: 0, narrative_chunks: 0 });
    const [loading, setLoading] = useState(true);
    const [editingItem, setEditingItem] = useState(null); // { mode: 'edit'|'add', data: {} }
    const [saving, setSaving] = useState(false);
    const [expandedIdx, setExpandedIdx] = useState(null); // which item index is expanded

    // ── Load materials ──
    useEffect(() => {
        loadMaterials();
    }, []);

    const loadMaterials = async () => {
        setLoading(true);
        try {
            const [matRes, sumRes] = await Promise.all([
                fetch(`${API_BASE}/api/bidding/materials`),
                fetch(`${API_BASE}/api/bidding/materials/summary`),
            ]);
            const matData = await matRes.json();
            const sumData = await sumRes.json();
            if (matData.success) setMaterials(matData.data);
            if (sumData.success) setSummary(sumData.data);
        } catch (e) {
            console.error('Failed to load materials:', e);
        } finally {
            setLoading(false);
        }
    };

    // ── Delete ──
    const handleDelete = async (tab, item) => {
        const keyField = KEY_FIELD[tab];
        const name = item[keyField];
        if (!confirm(`确定删除 "${name}"？`)) return;

        const endpoint = tab === 'projects'
            ? `${API_BASE}/api/bidding/materials/projects/${encodeURIComponent(name)}`
            : tab === 'resumes'
                ? `${API_BASE}/api/bidding/materials/resumes/${encodeURIComponent(name)}`
                : `${API_BASE}/api/bidding/materials/qualifications/${encodeURIComponent(name)}`;

        try {
            const res = await fetch(endpoint, { method: 'DELETE' });
            const result = await res.json();
            if (result.success) {
                loadMaterials();
            }
        } catch (e) {
            console.error('Delete failed:', e);
        }
    };

    // ── Save (edit or add) ──
    const handleSave = async () => {
        if (!editingItem) return;
        setSaving(true);

        try {
            if (editingItem.mode === 'add') {
                const res = await fetch(`${API_BASE}/api/bidding/materials/add`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ type: activeTab, data: editingItem.data }),
                });
                await res.json();
            } else {
                const keyField = KEY_FIELD[activeTab];
                const name = editingItem.originalName || editingItem.data[keyField];
                const endpoint = activeTab === 'projects'
                    ? `${API_BASE}/api/bidding/materials/projects/${encodeURIComponent(name)}`
                    : activeTab === 'resumes'
                        ? `${API_BASE}/api/bidding/materials/resumes/${encodeURIComponent(name)}`
                        : `${API_BASE}/api/bidding/materials/qualifications/${encodeURIComponent(name)}`;

                const res = await fetch(endpoint, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ updates: editingItem.data }),
                });
                await res.json();
            }

            setEditingItem(null);
            loadMaterials();
        } catch (e) {
            console.error('Save failed:', e);
        } finally {
            setSaving(false);
        }
    };

    // ── Render item list ──
    const renderList = () => {
        const items = materials[activeTab] || [];
        const fields = FIELD_MAP[activeTab];
        const keyField = KEY_FIELD[activeTab];

        if (loading) {
            return (
                <div className="flex items-center justify-center py-16 text-zinc-500">
                    <Loader2 size={20} className="animate-spin mr-2" />
                    加载中...
                </div>
            );
        }

        if (!items.length) {
            return (
                <div className="text-center py-16 text-zinc-500 text-sm">
                    暂无数据，点击「+ 新增」添加
                </div>
            );
        }

        return (
            <div className="divide-y divide-zinc-800">
                {items.map((item, idx) => {
                    const isExpanded = expandedIdx === idx;
                    return (
                        <div key={idx}>
                            <div
                                onClick={() => setExpandedIdx(isExpanded ? null : idx)}
                                className={`flex items-center justify-between px-4 py-3 cursor-pointer transition-colors group ${isExpanded ? 'bg-zinc-800/70' : 'hover:bg-zinc-800/50'
                                    }`}>
                                <div className="flex items-center space-x-2 flex-1 min-w-0">
                                    {isExpanded
                                        ? <ChevronDown size={14} className="text-orange-400 shrink-0" />
                                        : <ChevronRight size={14} className="text-zinc-600 shrink-0" />
                                    }
                                    <span className="text-[13px] font-semibold text-zinc-100">
                                        {item[keyField] || '未命名'}
                                    </span>
                                    {activeTab === 'resumes' && item.title && (
                                        <span className="text-[11px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                                            {item.title}
                                        </span>
                                    )}
                                    {activeTab === 'resumes' && item.specialty && (
                                        <span className="text-[11px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                            {item.specialty}
                                        </span>
                                    )}
                                    {activeTab === 'projects' && item.project_type && (
                                        <span className="text-[11px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                                            {item.project_type}
                                        </span>
                                    )}
                                </div>
                                <div className="flex items-center space-x-1">
                                    <div className="text-[11px] text-zinc-500 mr-2 hidden sm:block">
                                        {activeTab === 'resumes' && (
                                            <>执业{item.years_of_practice || '?'}年{item.education ? ` · ${item.education}` : ''}</>
                                        )}
                                        {activeTab === 'projects' && (
                                            <>{item.client || ''}{item.contract_amount ? ` · ${item.contract_amount}` : ''}</>
                                        )}
                                        {activeTab === 'qualifications' && (
                                            <>{item.issuer || ''}{item.valid_until ? ` · 至${item.valid_until}` : ''}</>
                                        )}
                                    </div>
                                    <button onClick={(e) => { e.stopPropagation(); setEditingItem({ mode: 'edit', data: { ...item }, originalName: item[keyField] }); }}
                                        className="p-1.5 rounded hover:bg-zinc-700 text-zinc-400 hover:text-blue-300 transition-colors opacity-0 group-hover:opacity-100"
                                        title="编辑">
                                        <Edit3 size={13} />
                                    </button>
                                    <button onClick={(e) => { e.stopPropagation(); handleDelete(activeTab, item); }}
                                        className="p-1.5 rounded hover:bg-zinc-700 text-zinc-400 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
                                        title="删除">
                                        <Trash2 size={13} />
                                    </button>
                                </div>
                            </div>
                            {/* ── Expanded detail panel ── */}
                            {isExpanded && (
                                <div className="bg-zinc-850 border-l-2 border-orange-500/40 mx-4 mb-2 rounded-md bg-zinc-900/80 px-4 py-3">
                                    <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                                        {fields.map(f => {
                                            const val = item[f.key];
                                            if (val === undefined || val === null || val === '') return null;
                                            return (
                                                <div key={f.key} className={f.multiline || f.array ? 'col-span-2' : ''}>
                                                    <span className="text-[10px] text-zinc-500 uppercase tracking-wide">{f.label}</span>
                                                    {f.array && Array.isArray(val) ? (
                                                        <div className="mt-0.5">
                                                            {val.map((v, vi) => (
                                                                <div key={vi} className="text-[12px] text-zinc-300 flex items-start">
                                                                    <span className="text-orange-400 mr-1.5 mt-0.5">•</span>
                                                                    <span>{typeof v === 'string' ? v : JSON.stringify(v)}</span>
                                                                </div>
                                                            ))}
                                                            {!val.length && <span className="text-[12px] text-zinc-600">—</span>}
                                                        </div>
                                                    ) : (
                                                        <div className="text-[12px] text-zinc-200 mt-0.5">
                                                            {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}
                                        {/* Show any extra fields not in FIELD_MAP */}
                                        {Object.entries(item).filter(([k]) => !fields.some(f => f.key === k) && k !== '_source').map(([k, v]) => {
                                            if (v === undefined || v === null || v === '') return null;
                                            return (
                                                <div key={k} className={Array.isArray(v) ? 'col-span-2' : ''}>
                                                    <span className="text-[10px] text-zinc-500 uppercase tracking-wide">{k}</span>
                                                    {Array.isArray(v) ? (
                                                        <div className="mt-0.5">
                                                            {v.map((vi, i) => (
                                                                <div key={i} className="text-[12px] text-zinc-300 flex items-start">
                                                                    <span className="text-orange-400 mr-1.5 mt-0.5">•</span>
                                                                    <span>{typeof vi === 'string' ? vi : JSON.stringify(vi)}</span>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    ) : (
                                                        <div className="text-[12px] text-zinc-200 mt-0.5">
                                                            {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        );
    };

    // ── Render edit/add form ──
    const renderForm = () => {
        if (!editingItem) return null;
        const fields = FIELD_MAP[activeTab];

        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                <div className="bg-zinc-900 border border-zinc-700 rounded-xl w-[480px] max-h-[80vh] overflow-y-auto shadow-2xl">
                    <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-700">
                        <h3 className="text-sm font-bold text-zinc-100">
                            {editingItem.mode === 'add' ? '+ 新增' : '✏️ 编辑'} {TABS.find(t => t.key === activeTab)?.label}
                        </h3>
                        <button onClick={() => setEditingItem(null)} className="text-zinc-500 hover:text-zinc-300">
                            <X size={16} />
                        </button>
                    </div>
                    <div className="px-5 py-4 space-y-3">
                        {fields.map(f => (
                            <div key={f.key}>
                                <label className="block text-[11px] text-zinc-400 mb-1">
                                    {f.label} {f.required && <span className="text-orange-400">*</span>}
                                </label>
                                {f.multiline ? (
                                    <textarea
                                        value={editingItem.data[f.key] || ''}
                                        onChange={(e) => setEditingItem(prev => ({
                                            ...prev, data: { ...prev.data, [f.key]: e.target.value }
                                        }))}
                                        rows={3}
                                        className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-[12px] text-zinc-100 focus:border-orange-500/60 focus:outline-none transition-colors resize-none"
                                    />
                                ) : (
                                    <input
                                        type="text"
                                        value={editingItem.data[f.key] || ''}
                                        onChange={(e) => setEditingItem(prev => ({
                                            ...prev, data: { ...prev.data, [f.key]: e.target.value }
                                        }))}
                                        className="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-[12px] text-zinc-100 focus:border-orange-500/60 focus:outline-none transition-colors"
                                    />
                                )}
                            </div>
                        ))}
                    </div>
                    <div className="flex items-center justify-end space-x-2 px-5 py-3 border-t border-zinc-700">
                        <button onClick={() => setEditingItem(null)}
                            className="px-4 py-2 rounded-md text-[11px] font-bold text-zinc-400 hover:text-zinc-200 transition-colors">
                            取消
                        </button>
                        <button onClick={handleSave} disabled={saving}
                            className="flex items-center space-x-1.5 px-4 py-2 rounded-md text-[11px] font-bold bg-orange-500/20 border border-orange-500/40 text-orange-300 hover:bg-orange-500/30 transition-all disabled:opacity-40">
                            {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
                            <span>{saving ? '保存中...' : '保存'}</span>
                        </button>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
                <div className="flex items-center space-x-3">
                    <button onClick={onClose}
                        className="flex items-center space-x-1 text-[11px] text-zinc-400 hover:text-zinc-200 transition-colors">
                        <ArrowLeft size={14} />
                        <span>返回</span>
                    </button>
                    <h2 className="text-sm font-bold text-zinc-100">📦 素材库管理</h2>
                    <div className="flex items-center space-x-2 text-[10px] text-zinc-500">
                        <span>{summary.resumes}简历</span>
                        <span>·</span>
                        <span>{summary.projects}项目</span>
                        <span>·</span>
                        <span>{summary.qualifications}资质</span>
                        <span>·</span>
                        <span>{summary.narrative_chunks}范文</span>
                    </div>
                </div>
                <button onClick={() => setEditingItem({ mode: 'add', data: {} })}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-[11px] font-bold bg-orange-500/20 border border-orange-500/40 text-orange-300 hover:bg-orange-500/30 transition-all">
                    <Plus size={12} />
                    <span>新增</span>
                </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-zinc-800">
                {TABS.map(tab => {
                    const count = (materials[tab.key] || []).length;
                    return (
                        <button key={tab.key}
                            onClick={() => setActiveTab(tab.key)}
                            className={`flex items-center space-x-1.5 px-4 py-2.5 text-[12px] font-medium border-b-2 transition-all ${activeTab === tab.key
                                ? 'border-orange-500 text-orange-300'
                                : 'border-transparent text-zinc-500 hover:text-zinc-300'
                                }`}>
                            <span>{tab.emoji}</span>
                            <span>{tab.label}</span>
                            <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${activeTab === tab.key ? 'bg-orange-500/20 text-orange-300' : 'bg-zinc-800 text-zinc-500'
                                }`}>{count}</span>
                        </button>
                    );
                })}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto">
                {renderList()}
            </div>

            {/* Edit/Add Form Modal */}
            {renderForm()}
        </div>
    );
}
