import { useState, useEffect } from 'react';
import { Activity, Eye, X, Shield, AlertTriangle, CheckCircle } from 'lucide-react';
import { getResourceMetrics, getActiveSessions, getNerRules, terminateSession } from '../api/services';

const tabItems = ['资源监控', 'NER 脱敏沙盒', '算力账单'];

// NER 规则 + 匹配正则
const nerRulesDef = [
    { id: 'per', label: '人名识别脱敏 (Identity)', enabled: true, pattern: /(张三|李四|王伟|陈刚|赵敏|周律师|刘律师)/g, tag: 'PER' },
    { id: 'org', label: '机构/律所名称 (Org)', enabled: true, pattern: /(深圳市腾讯计算机系统有限公司|北京市金杜律师事务所|某市人民政府)/g, tag: 'ORG' },
    { id: 'amt', label: '敏感数值模糊 (Financial)', enabled: true, pattern: /(500万元|120万元|80亿元|150亿元)/g, tag: 'AMT' },
    { id: 'case', label: '法律案号识别 (CaseID)', enabled: true, pattern: /(\(2024\)沪74民终2113号|\(2023\)京01民初456号)/g, tag: 'CASE' },
    { id: 'idcard', label: '身份证号 (IDCard)', enabled: true, pattern: /(310[0-9]{15}|110[0-9]{15})/g, tag: 'ID' },
    { id: 'phone', label: '手机号码 (Phone)', enabled: true, pattern: /(1[3-9]\d{9})/g, tag: 'PHONE' },
];

const sampleText = '贵公司合同编号(2024)沪74民终2113号案件中，深圳市腾讯计算机系统有限公司委托张三律师与李四律师处理涉案金额500万元的知识产权纠纷。张三律师联系电话13912345678，身份证号310101199001011234。';

export default function Settings() {
    const [tab, setTab] = useState(1); // 默认展示 NER 沙盒
    const [resources, setResources] = useState([]);
    const [sessions, setSessions] = useState([]);
    const [rules, setRules] = useState(nerRulesDef);
    const [nerInput, setNerInput] = useState(sampleText);
    const [detections, setDetections] = useState([]);

    useEffect(() => {
        getResourceMetrics().then(setResources);
        getActiveSessions().then(setSessions);
    }, []);

    // NER 实时检测
    useEffect(() => {
        const found = [];
        const enabledRules = rules.filter(r => r.enabled);
        enabledRules.forEach(rule => {
            let match;
            const re = new RegExp(rule.pattern.source, rule.pattern.flags);
            while ((match = re.exec(nerInput)) !== null) {
                found.push({ text: match[0], tag: rule.tag, start: match.index, end: match.index + match[0].length, ruleId: rule.id });
            }
        });
        found.sort((a, b) => a.start - b.start);
        setDetections(found);
    }, [nerInput, rules]);

    const toggleRule = (id) => setRules(rules.map(r => r.id === id ? { ...r, enabled: !r.enabled } : r));

    // 生成带标注的 HTML
    const renderAnnotatedText = () => {
        if (detections.length === 0) return <span className="text-zinc-300">{nerInput}</span>;
        const parts = [];
        let lastEnd = 0;
        detections.forEach((d, i) => {
            if (d.start > lastEnd) {
                parts.push(<span key={`t-${i}`} className="text-zinc-300">{nerInput.slice(lastEnd, d.start)}</span>);
            }
            parts.push(
                <span key={`d-${i}`} className="relative inline-block group">
                    <span className="line-through text-red-400/70 decoration-red-500 decoration-2">{d.text}</span>
                    <span className="ml-1 px-1.5 py-0.5 bg-emerald-500/20 text-emerald-400 text-[9px] font-bold rounded border border-emerald-500/30 uppercase">[{d.tag}-{String(i + 1).padStart(3, '0')}]</span>
                </span>
            );
            lastEnd = d.end;
        });
        if (lastEnd < nerInput.length) {
            parts.push(<span key="tail" className="text-zinc-300">{nerInput.slice(lastEnd)}</span>);
        }
        return parts;
    };

    // 生成脱敏后纯文本
    const getMaskedText = () => {
        if (detections.length === 0) return nerInput;
        let result = '';
        let lastEnd = 0;
        detections.forEach((d, i) => {
            result += nerInput.slice(lastEnd, d.start);
            result += `[${d.tag}-${String(i + 1).padStart(3, '0')}]`;
            lastEnd = d.end;
        });
        result += nerInput.slice(lastEnd);
        return result;
    };

    const tagColors = { PER: 'text-blue-400', ORG: 'text-purple-400', AMT: 'text-amber-400', CASE: 'text-cyan-400', ID: 'text-red-400', PHONE: 'text-rose-400' };

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

            {/* Tab 0: 资源监控 */}
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

            {/* Tab 1: NER 脱敏沙盒 */}
            {tab === 1 && (
                <div className="space-y-5 slide-up">
                    {/* 规则配置 */}
                    <div className="bg-white border border-zinc-200 rounded-sm p-5">
                        <div className="flex items-center space-x-2 mb-3">
                            <Shield size={14} className="text-blue-600" />
                            <h3 className="font-bold text-sm text-zinc-700 uppercase tracking-tight">NER 脱敏规则配置</h3>
                            <span className="text-[9px] text-emerald-600 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">{rules.filter(r => r.enabled).length}/{rules.length} 已启用</span>
                        </div>
                        <div className="grid grid-cols-3 gap-2">
                            {rules.map((r) => (
                                <label key={r.id} className="flex items-center space-x-2 cursor-pointer group bg-zinc-50 rounded-sm px-3 py-2 border border-zinc-100 hover:border-blue-200 transition">
                                    <input type="checkbox" checked={r.enabled} onChange={() => toggleRule(r.id)} className="accent-blue-600 w-3.5 h-3.5" />
                                    <span className={`text-[11px] font-bold transition ${r.enabled ? 'text-zinc-700' : 'text-zinc-400 line-through'}`}>{r.label}</span>
                                </label>
                            ))}
                        </div>
                    </div>

                    {/* 输入 + 标注输出 */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="bg-white border border-zinc-200 rounded-sm p-4">
                            <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-2 flex items-center"><Eye size={12} className="mr-1" />原始文本 (Raw Input)</div>
                            <textarea value={nerInput} onChange={(e) => setNerInput(e.target.value)} rows={7}
                                className="w-full border border-zinc-300 rounded-sm p-3 text-[12px] font-mono focus:outline-none focus:border-blue-500 resize-none bg-zinc-50 shadow-inner leading-relaxed" />
                        </div>
                        <div className="bg-[#151921] border border-zinc-700 rounded-sm p-4 shadow-inner">
                            <div className="text-[10px] font-bold text-emerald-500 uppercase tracking-widest mb-2 flex items-center justify-between">
                                <span>🔍 实时标注结果 (Live Annotation)</span>
                                <span className="text-[9px] text-zinc-500">{detections.length} entities found</span>
                            </div>
                            <div className="text-[12px] font-mono whitespace-pre-wrap leading-relaxed min-h-[120px]">
                                {renderAnnotatedText()}
                            </div>
                        </div>
                    </div>

                    {/* 检测统计 + 脱敏结果 */}
                    <div className="grid grid-cols-12 gap-4">
                        <div className="col-span-4 bg-white border border-zinc-200 rounded-sm p-4">
                            <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-3">实体检测统计</p>
                            <div className="space-y-2">
                                {['PER', 'ORG', 'AMT', 'CASE', 'ID', 'PHONE'].map(tag => {
                                    const count = detections.filter(d => d.tag === tag).length;
                                    if (count === 0) return null;
                                    return (
                                        <div key={tag} className="flex items-center justify-between py-1.5 px-2 bg-zinc-50 rounded-sm">
                                            <span className={`text-[11px] font-bold ${tagColors[tag]}`}>{tag}</span>
                                            <span className="text-xs font-bold text-zinc-700">{count}</span>
                                        </div>
                                    );
                                })}
                                <div className="pt-2 mt-2 border-t border-zinc-200 flex justify-between">
                                    <span className="text-[11px] font-bold text-zinc-600">总计</span>
                                    <span className="text-sm font-bold text-blue-600">{detections.length} 处</span>
                                </div>
                            </div>
                        </div>
                        <div className="col-span-8 bg-[#0f1117] border border-zinc-800 rounded-sm p-4">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-[10px] font-bold text-emerald-500 uppercase tracking-widest">脱敏后输出 (De-Identified Output)</span>
                                <span className="text-[9px] text-zinc-600 font-bold">Safe to Send to LLM ✓</span>
                            </div>
                            <div className="text-[11px] text-emerald-300/80 font-mono whitespace-pre-wrap leading-relaxed bg-black/30 p-3 rounded border border-zinc-800">
                                {getMaskedText()}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Tab 2: 算力账单 */}
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
