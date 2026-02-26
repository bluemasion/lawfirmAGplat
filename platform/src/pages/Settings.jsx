import { useState, useEffect } from 'react';
import { Activity, Eye, X } from 'lucide-react';
import { getResourceMetrics, getActiveSessions, getNerRules, runNerMask, terminateSession } from '../api/services';

const tabItems = ['资源监控', 'NER 脱敏配置', '算力账单'];

export default function Settings() {
    const [tab, setTab] = useState(0);
    const [resources, setResources] = useState([]);
    const [sessions, setSessions] = useState([]);
    const [rules, setRules] = useState([]);
    const [nerInput, setNerInput] = useState('贵公司合同编号(2024)沪74民终2113号案件中，深圳市腾讯计算机系统有限公司委托张三律师与李四律师处理涉案金额500万元的知识产权纠纷。');
    const [nerOutput, setNerOutput] = useState('');

    useEffect(() => {
        getResourceMetrics().then(setResources);
        getActiveSessions().then(setSessions);
        getNerRules().then(setRules);
    }, []);

    useEffect(() => { runNerMask(nerInput, rules).then(setNerOutput); }, [nerInput, rules]);

    const toggleRule = (id) => setRules(rules.map(r => r.id === id ? { ...r, enabled: !r.enabled } : r));

    const bgForColor = (c) => ({ emerald: 'bg-emerald-500', blue: 'bg-blue-500', amber: 'bg-amber-500', rose: 'bg-rose-500' })[c] || 'bg-zinc-500';

    return (
        <div className="p-8 animate-in">
            <div className="flex justify-between items-end border-b border-zinc-200 pb-4 mb-8">
                <h2 className="text-xl font-bold text-zinc-800 uppercase tracking-tighter">平台治理中心 / Platform Admin</h2>
            </div>
            <div className="flex space-x-1 mb-8 bg-zinc-100 p-1 rounded-sm border border-zinc-200 shadow-inner">
                {tabItems.map((t, i) => (
                    <button key={i} onClick={() => setTab(i)}
                        className={`flex-1 py-2.5 text-xs font-bold rounded-sm transition-all uppercase tracking-tight ${i === tab ? 'bg-white text-blue-700 shadow-sm border border-zinc-200' : 'text-zinc-500 hover:text-zinc-700'}`}>{t}</button>
                ))}
            </div>

            {tab === 0 && (
                <div className="space-y-6 slide-up">
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        {resources.map((r, i) => (
                            <div key={i} className="bg-white border border-zinc-200 rounded-sm p-4 shadow-sm">
                                <div className="flex justify-between text-[10px] font-bold text-zinc-500 uppercase mb-3 tracking-widest"><span>{r.label}</span><span className="text-zinc-900">{r.usage}%</span></div>
                                <div className="w-full bg-zinc-100 h-2 rounded-full overflow-hidden mb-2 shadow-inner"><div className={`h-full ${bgForColor(r.color)} transition-all`} style={{ width: `${r.usage}%` }}></div></div>
                                <div className="text-[10px] text-zinc-400 font-bold italic">{r.details}</div>
                            </div>
                        ))}
                    </div>
                    <div className="bg-white border border-zinc-300 rounded-sm overflow-hidden shadow-sm">
                        <div className="px-4 py-3 bg-zinc-50 border-b border-zinc-200 flex justify-between items-center text-[10px] font-bold text-zinc-500 uppercase tracking-widest">
                            <span>在线会话审计 (Active Sessions)</span>
                            <span className="flex items-center text-emerald-600"><Activity size={10} className="mr-1 animate-pulse" /> {sessions.length} Active</span>
                        </div>
                        <table className="w-full text-left text-[11px]">
                            <thead className="border-b border-zinc-200 text-zinc-500"><tr><th className="px-6 py-3">在线用户</th><th className="px-6 py-3">当前活动</th><th className="px-6 py-3 text-right">操作</th></tr></thead>
                            <tbody className="divide-y divide-zinc-100">
                                {sessions.map((s, i) => (
                                    <tr key={i} className="hover:bg-zinc-50"><td className="px-6 py-3 font-bold">{s.name}</td><td className="px-6 py-3 text-zinc-500 italic">{s.activity}</td>
                                        <td className="px-6 py-3 text-right">
                                            <button onClick={() => terminateSession(i)} className="text-[10px] font-bold text-red-600 border border-red-200 bg-red-50 px-3 py-1 rounded-sm hover:bg-red-100 uppercase">Terminate</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {tab === 1 && (
                <div className="space-y-6 slide-up">
                    <div className="bg-white border border-zinc-200 rounded-sm p-6 space-y-4">
                        <h3 className="font-bold text-sm text-zinc-700 uppercase tracking-tight">NER 脱敏规则配置</h3>
                        {rules.map((r) => (
                            <label key={r.id} className="flex items-center space-x-3 cursor-pointer group">
                                <input type="checkbox" checked={r.enabled} onChange={() => toggleRule(r.id)} className="accent-blue-600 w-4 h-4" />
                                <span className={`text-xs font-bold transition ${r.enabled ? 'text-zinc-700' : 'text-zinc-400 line-through'}`}>{r.label}</span>
                            </label>
                        ))}
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="bg-white border border-zinc-200 rounded-sm p-4">
                            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-2 flex items-center"><Eye size={12} className="mr-1" />原始文本 (Raw Input)</div>
                            <textarea value={nerInput} onChange={(e) => setNerInput(e.target.value)} rows={6}
                                className="w-full border border-zinc-300 rounded-sm p-3 text-[11px] font-mono focus:outline-none focus:border-blue-500 resize-none bg-zinc-50 shadow-inner" />
                        </div>
                        <div className="bg-[#151921] border border-zinc-700 rounded-sm p-4 shadow-inner">
                            <div className="text-[10px] font-bold text-emerald-500 uppercase tracking-widest mb-2">脱敏后预览 (De-Identified Preview)</div>
                            <div className="text-[11px] text-zinc-300 font-mono whitespace-pre-wrap leading-relaxed">{nerOutput}</div>
                        </div>
                    </div>
                </div>
            )}

            {tab === 2 && (
                <div className="bg-white border border-zinc-200 rounded-sm p-12 text-center slide-up">
                    <div className="text-6xl mb-4 opacity-30">📊</div>
                    <p className="text-zinc-500 text-sm font-bold">算力账单模块建设中</p>
                    <p className="text-zinc-400 text-[10px] mt-1 italic uppercase tracking-wide">Billing Module Under Development</p>
                </div>
            )}
        </div>
    );
}
