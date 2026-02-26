import { ArrowLeft, CheckCircle, AlertTriangle } from 'lucide-react';

const steps = [
    { label: '数据采集', desc: '从案管系统抓取律师业绩、资质及项目经验', done: true },
    { label: '智能编排', desc: '根据招标文件要求，AI 自动匹配最优团队组合', done: true },
    { label: '合规审核', desc: '扫描《律师法》禁止用语，拦截违规表述', done: false },
];

export default function BiddingAgent({ onBack }) {
    return (
        <div className="p-6 space-y-6 animate-in">
            <div className="flex items-center space-x-3 border-b border-zinc-200 pb-4">
                <button onClick={onBack} className="text-zinc-400 hover:text-zinc-700"><ArrowLeft size={16} /></button>
                <div>
                    <h2 className="text-lg font-bold text-zinc-800 uppercase tracking-tight">智能投标中心 (Bidding Studio)</h2>
                    <p className="text-[10px] text-zinc-400 font-bold uppercase tracking-widest">Automated Bid Preparation with Compliance Guardrails</p>
                </div>
            </div>

            <div className="flex items-center space-x-4 mb-6">
                {steps.map((s, i) => (
                    <div key={i} className="flex items-center">
                        <div className={`flex items-center space-x-2 px-4 py-3 rounded-sm border transition-all ${s.done ? 'bg-emerald-50 border-emerald-200' : 'bg-zinc-50 border-zinc-200 animate-pulse'}`}>
                            {s.done ? <CheckCircle size={16} className="text-emerald-600" /> : <div className="w-4 h-4 border-2 border-blue-400 rounded-full border-t-transparent animate-spin"></div>}
                            <div>
                                <p className={`text-xs font-bold ${s.done ? 'text-emerald-700' : 'text-blue-600'}`}>{s.label}</p>
                                <p className="text-[9px] text-zinc-400 italic">{s.desc}</p>
                            </div>
                        </div>
                        {i < steps.length - 1 && <div className="w-8 h-px bg-zinc-300 mx-2"></div>}
                    </div>
                ))}
            </div>

            <div className="grid grid-cols-12 gap-6">
                <div className="col-span-8 bg-white border border-zinc-200 rounded-sm overflow-hidden shadow-sm">
                    <div className="px-4 py-3 bg-zinc-50 border-b border-zinc-200 text-[10px] font-bold text-zinc-500 uppercase tracking-widest">标书草案预览 (Draft Preview)</div>
                    <div className="p-6 space-y-4 text-[12px] text-zinc-700 leading-relaxed font-serif">
                        <h3 className="text-sm font-bold text-zinc-900 uppercase tracking-tight">第三章 项目团队 — 核心成员介绍</h3>
                        <div className="bg-zinc-50 border border-zinc-100 rounded-sm p-4 space-y-2">
                            <p><strong>项目负责人：王大明律师</strong></p>
                            <p>执业年限：18年 | 专业领域：IPO、并购重组</p>
                            <p>代表业绩：主办/协办 IPO 项目 12 个，累计募资规模超过人民币 80 亿元。曾主办某科创板上市公司首发并上市项目。</p>
                        </div>
                        <div className="bg-zinc-50 border border-zinc-100 rounded-sm p-4 space-y-2">
                            <p><strong>项目成员：李晓云律师</strong></p>
                            <p>执业年限：8年 | 专业领域：证券合规、基金备案</p>
                            <p>代表业绩：参与债券发行项目 6 个，累计发行规模超过人民币 150 亿元。</p>
                        </div>
                    </div>
                </div>
                <div className="col-span-4 space-y-4">
                    <div className="bg-[#151921] border border-zinc-700 rounded-sm p-5 text-white shadow-inner">
                        <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-3">合规审核面板</h4>
                        <div className="space-y-3">
                            <div className="flex items-start space-x-2 text-[11px]">
                                <AlertTriangle size={14} className="text-amber-500 mt-0.5 shrink-0" />
                                <div>
                                    <p className="text-amber-400 font-bold">检测到违规用语</p>
                                    <p className="text-zinc-400 italic mt-1">"胜诉率高达95%" — 违反《律师法》第26条，禁止对办案结果做出承诺。</p>
                                    <p className="text-blue-400 mt-1 text-[10px]">建议替换为："在同类案件中具有丰富经验"</p>
                                </div>
                            </div>
                            <div className="flex items-start space-x-2 text-[11px]">
                                <CheckCircle size={14} className="text-emerald-500 mt-0.5 shrink-0" />
                                <div>
                                    <p className="text-emerald-400 font-bold">团队资质验证通过</p>
                                    <p className="text-zinc-400 italic mt-1">所有成员执业证均在有效期内，无行业处分记录。</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    <button className="w-full py-3 bg-blue-600 text-white text-xs font-bold rounded-sm uppercase tracking-tight hover:bg-blue-700 transition shadow-lg">导出标书 (Export .docx)</button>
                </div>
            </div>
        </div>
    );
}
