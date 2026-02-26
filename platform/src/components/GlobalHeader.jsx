import { Search, Grid, ChevronDown, Shield } from 'lucide-react';

export default function GlobalHeader({ onReset }) {
    return (
        <div className="bg-[#151921] text-white h-12 flex items-center justify-between px-4 z-50 shadow-md shrink-0">
            <div className="flex items-center space-x-6">
                <div className="flex items-center space-x-2 cursor-pointer group" onClick={onReset}>
                    <div className="w-6 h-6 bg-orange-500 rounded-sm flex items-center justify-center font-bold text-xs italic text-white shadow-sm">L</div>
                    <span className="font-bold text-sm tracking-tight uppercase group-hover:text-orange-400 transition-colors">律所 AI 控制台</span>
                </div>
                <div className="h-6 w-px bg-zinc-700"></div>
                <div className="flex items-center space-x-1 text-zinc-400 text-xs hover:text-white cursor-pointer transition">
                    <Grid size={14} /><span>应用中心</span><ChevronDown size={14} />
                </div>
            </div>
            <div className="flex-1 max-w-2xl px-8">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" size={14} />
                    <input type="text" placeholder="搜索法律 Agent、底稿卷宗或安全审计日志..."
                        className="w-full bg-[#2a3139] border-zinc-700 border text-[11px] py-1.5 pl-10 pr-4 rounded focus:outline-none focus:border-orange-500 transition-colors placeholder:text-zinc-600 font-medium" />
                </div>
            </div>
            <div className="flex items-center space-x-5">
                <div className="flex items-center space-x-1 text-emerald-500 text-[10px] font-bold border border-emerald-900/30 bg-emerald-950/20 px-2 py-1 rounded-sm uppercase tracking-tighter">
                    <Shield size={14} /><span className="hidden lg:inline">VPC 已加密连接</span>
                </div>
                <div className="flex items-center space-x-2 bg-zinc-800 px-3 py-1 rounded-sm cursor-pointer border border-zinc-700 hover:bg-zinc-700 transition shadow-sm">
                    <div className="w-5 h-5 bg-blue-600 rounded-full flex items-center justify-center text-[10px] font-bold text-white uppercase font-serif italic">W</div>
                    <span className="text-xs font-bold whitespace-nowrap">王大明 @ 天元律所</span>
                    <ChevronDown size={12} className="text-zinc-500" />
                </div>
            </div>
        </div>
    );
}
