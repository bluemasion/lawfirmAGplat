import { useState, useEffect } from 'react';
import { ArrowLeft, Folder, FileText, Shield, AlertTriangle, Eye, Terminal } from 'lucide-react';
import { getSecuritiesFiles } from '../api/services';

export default function SecuritiesAgent({ onBack }) {
    const [files, setFiles] = useState([]);
    const [selected, setSelected] = useState(null);
    useEffect(() => { getSecuritiesFiles().then(setFiles); }, []);

    return (
        <div className="p-6 space-y-6 animate-in">
            <div className="flex items-center space-x-3 border-b border-zinc-200 pb-4">
                <button onClick={onBack} className="text-zinc-400 hover:text-zinc-700"><ArrowLeft size={16} /></button>
                <div>
                    <h2 className="text-lg font-bold text-zinc-800 uppercase tracking-tight">证券底稿核查引擎</h2>
                    <p className="text-[10px] text-zinc-400 font-bold uppercase tracking-widest">Securities Working Paper Verification Engine</p>
                </div>
            </div>
            <div className="grid grid-cols-12 gap-6 min-h-[500px]">
                <div className="col-span-3 bg-white border border-zinc-200 rounded-sm overflow-hidden shadow-sm">
                    <div className="px-4 py-3 bg-zinc-50 border-b border-zinc-200 text-[10px] font-bold text-zinc-500 uppercase tracking-widest flex items-center">
                        <Folder size={12} className="mr-1.5" /> 卷宗目录
                    </div>
                    <div className="divide-y divide-zinc-100">
                        {files.map((f, i) => (
                            <div key={i} onClick={() => setSelected(i)} className={`px-4 py-3 text-[11px] flex items-center space-x-2 cursor-pointer transition-colors ${selected === i ? 'bg-blue-50 text-blue-700 font-bold' : 'text-zinc-600 hover:bg-zinc-50'}`}>
                                <FileText size={12} /><span className="truncate">{f}</span>
                            </div>
                        ))}
                    </div>
                </div>
                <div className="col-span-5 space-y-4">
                    <div className="bg-[#0d1117] border border-zinc-700 rounded-sm flex flex-col h-56 shadow-inner overflow-hidden">
                        <div className="px-4 py-2 bg-[#161b22] border-b border-zinc-800 text-[10px] font-bold text-zinc-500 flex items-center uppercase tracking-widest">
                            <Terminal size={12} className="mr-1.5" /> NER 脱敏处理日志
                        </div>
                        <div className="flex-1 p-4 font-mono text-[10px] text-emerald-400 overflow-y-auto space-y-1 leading-relaxed">
                            <p className="text-zinc-600">[Ready] Awaiting file selection...</p>
                            {selected !== null && (<>
                                <p>{'>'} Loading: {files[selected]}...</p>
                                <p>[NER] Scanning entities...</p>
                                <p className="text-amber-400">[NER] Found: 张三 → [PERSON_001]</p>
                                <p className="text-amber-400">[NER] Found: 深圳市腾讯计算机系统有限公司 → [ORG_A]</p>
                                <p className="text-cyan-400">[DONE] De-identification complete. 2 entities masked.</p>
                            </>)}
                        </div>
                    </div>
                    <div className="bg-white border border-zinc-200 rounded-sm p-5 flex-1 shadow-sm">
                        <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-3 flex items-center"><Eye size={12} className="mr-1.5" /> AI 审计异常预警 (Audit Findings)</h4>
                        {selected !== null ? (
                            <div className="space-y-3">
                                <div className="border-l-2 border-red-500 bg-red-50 p-3 rounded-r text-[11px]">
                                    <div className="flex items-center space-x-1 text-red-700 font-bold"><AlertTriangle size={14} /><span>HIGH: 金额不一致</span></div>
                                    <p className="text-red-600 mt-1 italic">招股书载明"未受行政处罚"，但底稿卷宗04-危废处理合同显示2023年环保罚款 ¥505,000。</p>
                                </div>
                                <div className="border-l-2 border-amber-500 bg-amber-50 p-3 rounded-r text-[11px]">
                                    <div className="flex items-center space-x-1 text-amber-700 font-bold"><AlertTriangle size={14} /><span>MEDIUM: 日期偏差</span></div>
                                    <p className="text-amber-600 mt-1 italic">访谈记录日期 (2024-03-15) 早于项目立项日期 (2024-03-20)，存在逻辑矛盾。</p>
                                </div>
                            </div>
                        ) : <p className="text-zinc-400 text-xs italic">请从左侧选择文件开始核查</p>}
                    </div>
                </div>
                <div className="col-span-4 bg-[#151921] border border-zinc-700 rounded-sm p-5 text-white shadow-inner">
                    <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-4 flex items-center"><Shield size={12} className="mr-1.5" /> 合规核查清单</h4>
                    <div className="space-y-3 text-[11px]">
                        {['财务数据一致性', '法律意见完整性', '关联交易披露', '知识产权权属', '环保合规审计'].map((item, i) => (
                            <div key={i} className="flex items-center justify-between px-3 py-2 bg-zinc-800/50 rounded-sm border border-zinc-800">
                                <span className="text-zinc-300 font-bold">{item}</span>
                                <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded-sm ${i === 0 ? 'text-red-400 bg-red-950' : i === 4 ? 'text-amber-400 bg-amber-950' : 'text-emerald-400 bg-emerald-950'}`}>
                                    {i === 0 ? 'FAIL' : i === 4 ? 'WARN' : 'PASS'}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
