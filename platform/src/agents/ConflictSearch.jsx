import { useState } from 'react';
import { ArrowLeft, Search as SearchIcon, AlertTriangle, CheckCircle, Loader2, Ban } from 'lucide-react';
import { searchConflict } from '../api/services';

export default function ConflictSearch({ onBack }) {
    const [query, setQuery] = useState('');
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);

    const handleScan = () => {
        if (!query.trim()) return;
        setLoading(true);
        setResult(null);
        searchConflict(query).then((r) => { setResult(r); setLoading(false); });
    };

    return (
        <div className="p-6 space-y-6 animate-in">
            <div className="flex items-center space-x-3 border-b border-zinc-200 pb-4">
                <button onClick={onBack} className="text-zinc-400 hover:text-zinc-700"><ArrowLeft size={16} /></button>
                <div>
                    <h2 className="text-lg font-bold text-zinc-800 uppercase tracking-tight">利冲检索助手</h2>
                    <p className="text-[10px] text-zinc-400 font-bold uppercase tracking-widest">Conflict of Interest — Semantic Deep Scan</p>
                </div>
            </div>
            <div className="max-w-3xl mx-auto space-y-6">
                <div className="bg-white border border-zinc-200 rounded-sm p-6 shadow-sm">
                    <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest block mb-2">输入检索对象（支持别名、简称穿透）</label>
                    <div className="flex space-x-3">
                        <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="例: 腾讯, Tencent Holdings, 深圳市腾讯计算机系统有限公司..."
                            className="flex-1 border border-zinc-300 rounded-sm px-4 py-3 text-sm focus:outline-none focus:border-blue-500 bg-zinc-50 shadow-inner"
                            onKeyDown={(e) => e.key === 'Enter' && handleScan()} />
                        <button onClick={handleScan} disabled={loading}
                            className="px-6 py-3 bg-[#151921] text-white text-xs font-bold rounded-sm uppercase tracking-tight hover:bg-black transition-all flex items-center space-x-2 disabled:opacity-50 shadow-lg">
                            {loading ? <Loader2 size={14} className="animate-spin" /> : <SearchIcon size={14} />}
                            <span>{loading ? '扫描中...' : '执行扫描'}</span>
                        </button>
                    </div>
                </div>

                {loading && (
                    <div className="bg-white border border-zinc-200 rounded-sm p-10 text-center shadow-sm slide-up">
                        <Loader2 size={32} className="animate-spin text-blue-600 mx-auto mb-3" />
                        <p className="text-xs font-bold text-zinc-500 uppercase animate-pulse">Scanning Private Knowledge Graph + Entity Linking Model...</p>
                    </div>
                )}

                {result && (
                    <div className="space-y-4 slide-up">
                        <div className={`border rounded-sm p-6 ${result.risk === 'HIGH' ? 'bg-red-50 border-red-300' : 'bg-emerald-50 border-emerald-300'}`}>
                            <div className="flex items-center space-x-2 mb-3">
                                {result.risk === 'HIGH' ? <AlertTriangle className="text-red-600" size={20} /> : <CheckCircle className="text-emerald-600" size={20} />}
                                <span className={`text-sm font-bold uppercase ${result.risk === 'HIGH' ? 'text-red-700' : 'text-emerald-700'}`}>
                                    Risk Level: {result.risk}
                                </span>
                            </div>
                            {result.matches.map((m, i) => (
                                <div key={i} className="flex items-center justify-between py-3 border-t border-zinc-200/50 text-sm">
                                    <div>
                                        <span className="font-bold text-zinc-800">{m.name}</span>
                                        <span className="ml-2 text-[10px] text-zinc-500 italic">({m.relation})</span>
                                    </div>
                                    <span className={`text-[10px] font-bold uppercase px-2 py-1 rounded-sm ${m.status.includes('当前') ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>{m.status}</span>
                                </div>
                            ))}
                        </div>
                        {result.risk === 'HIGH' && (
                            <div className="bg-[#151921] border border-zinc-700 rounded-sm p-5 text-white shadow-2xl">
                                <div className="flex items-center space-x-2 mb-3">
                                    <Ban size={16} className="text-red-500" />
                                    <span className="text-xs font-bold uppercase tracking-wider text-red-400">强制回避建议 (Mandatory Avoidance)</span>
                                </div>
                                <p className="text-[11px] text-zinc-400 leading-relaxed italic">
                                    基于本所《利益冲突管理办法》第12条，"腾讯科技"作为当前顾问客户的子公司，与检索目标存在直接关联。建议：1) 立即通知团队负责合伙人；2) 启动信息隔离墙（Chinese Wall）；3) 48小时内向合规委员会报备。
                                </p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
