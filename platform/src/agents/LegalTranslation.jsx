import { ArrowLeft, Book, Stamp, ChevronRight } from 'lucide-react';

export default function LegalTranslation({ onBack }) {
    return (
        <div className="p-6 space-y-6 animate-in">
            <div className="flex items-center space-x-3 border-b border-zinc-200 pb-4">
                <button onClick={onBack} className="text-zinc-400 hover:text-zinc-700"><ArrowLeft size={16} /></button>
                <div>
                    <h2 className="text-lg font-bold text-zinc-800 uppercase tracking-tight">法律高保真翻译 (Layout Engine)</h2>
                    <p className="text-[10px] text-zinc-400 font-bold uppercase tracking-widest">High-Fidelity Legal Translation with 1:1 Layout Preservation</p>
                </div>
            </div>
            <div className="grid grid-cols-2 gap-6 min-h-[400px]">
                <div className="bg-white border border-zinc-200 rounded-sm overflow-hidden shadow-sm flex flex-col">
                    <div className="px-4 py-3 bg-zinc-50 border-b border-zinc-200 text-[10px] font-bold text-zinc-500 uppercase tracking-widest">源文本 (Source — CN)</div>
                    <div className="flex-1 p-5 text-[12px] text-zinc-700 leading-relaxed space-y-3 font-serif">
                        <p>根据《中华人民共和国公司法》第一百四十二条之规定，发行人应当在招股说明书中披露其关联交易的具体内容、定价政策及公允性分析。</p>
                        <p>本所律师经核查后认为，上述关联交易不存在损害发行人及中小股东利益的情形。</p>
                    </div>
                </div>
                <div className="bg-white border border-zinc-200 rounded-sm overflow-hidden shadow-sm flex flex-col">
                    <div className="px-4 py-3 bg-zinc-50 border-b border-zinc-200 text-[10px] font-bold text-zinc-500 uppercase tracking-widest">
                        <span>译文 (Target — EN)</span>
                    </div>
                    <div className="flex-1 p-5 text-[12px] text-zinc-700 leading-relaxed space-y-3 font-serif italic">
                        <p>In accordance with Article 142 of the <span className="bg-blue-100 text-blue-800 px-1 rounded font-bold not-italic">Company Law of the People's Republic of China</span>, the Issuer shall disclose in its prospectus the specific details, pricing policies, and fairness analyses of its related-party transactions.</p>
                        <p>Upon verification, the lawyers of this Firm are of the opinion that the aforementioned related-party transactions do not prejudice the interests of the Issuer or its minority shareholders.</p>
                    </div>
                </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
                <div className="bg-white border border-zinc-200 rounded-sm p-4 flex items-center space-x-3 cursor-pointer hover:border-blue-500 transition group">
                    <Book size={20} className="text-zinc-400 group-hover:text-blue-600" />
                    <div><p className="text-xs font-bold text-zinc-700">术语库管理</p><p className="text-[10px] text-zinc-400 italic">已加载 1,284 专业术语对</p></div>
                    <ChevronRight size={14} className="ml-auto text-zinc-300" />
                </div>
                <div className="bg-white border border-zinc-200 rounded-sm p-4 flex items-center space-x-3 cursor-pointer hover:border-blue-500 transition group">
                    <Stamp size={20} className="text-zinc-400 group-hover:text-blue-600" />
                    <div><p className="text-xs font-bold text-zinc-700">印章版式锁定</p><p className="text-[10px] text-zinc-400 italic">LayoutLMv3 — Phase 4</p></div>
                    <ChevronRight size={14} className="ml-auto text-zinc-300" />
                </div>
                <div className="bg-zinc-50 border border-zinc-200 rounded-sm p-4 text-center">
                    <p className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">翻译质量评分</p>
                    <p className="text-3xl font-bold text-emerald-600 mt-1">96.7</p>
                    <p className="text-[9px] text-zinc-400 italic mt-1">BLEU Score (Calibrated)</p>
                </div>
            </div>
        </div>
    );
}
