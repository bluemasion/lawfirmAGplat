import { LayoutDashboard, Grid, Cpu, Settings, ChevronRight } from 'lucide-react';

const navigation = [
    { id: 'workbench', label: '控制台首页', icon: LayoutDashboard },
    { id: 'appcenter', label: '应用中心', icon: Grid },
    { id: 'modelhub', label: '算力实例', icon: Cpu },
    { id: 'settings', label: '平台管理', icon: Settings },
];

export default function Sidebar({ activeTab, activeAgent, testModel, onSelectTab }) {
    return (
        <aside className="w-[240px] bg-white border-r border-zinc-300 flex flex-col z-10 shadow-[4px_0_12px_rgba(0,0,0,0.03)] shrink-0">
            <div className="p-4 border-b border-zinc-100 flex items-center justify-between bg-zinc-50/50 uppercase font-bold text-[10px] text-zinc-400 tracking-widest shrink-0">
                <span>Main Navigation</span>
                <ChevronRight size={14} className="text-zinc-300" />
            </div>
            <nav className="flex-1 py-4 px-3 space-y-1.5 overflow-y-auto font-bold uppercase tracking-tight">
                {navigation.map((item) => {
                    const Icon = item.icon;
                    const isActive = activeTab === item.id && !activeAgent && !testModel;
                    return (
                        <button key={item.id} onClick={() => onSelectTab(item.id)}
                            className={`w-full flex items-center space-x-3 px-4 py-3 rounded-sm transition-all text-xs ${isActive ? 'bg-blue-50 text-blue-700 border border-blue-200 shadow-sm' : 'text-zinc-600 hover:bg-zinc-50 border border-transparent'}`}>
                            <Icon size={16} className={isActive ? 'text-blue-700' : 'text-zinc-400'} />
                            <span>{item.label}</span>
                        </button>
                    );
                })}
            </nav>
            <div className="p-4 border-t border-zinc-100 shrink-0">
                <div className="bg-[#1a1c23] rounded-sm p-4 text-white space-y-2 relative overflow-hidden shadow-inner cursor-default">
                    <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest z-10 relative leading-none mb-1">System Edition</p>
                    <p className="text-xs font-mono font-bold text-orange-400 z-10 relative uppercase">v2.0.8-Enterprise</p>
                    <Cpu size={44} className="absolute -right-2 -bottom-2 text-white/5 rotate-12" />
                </div>
            </div>
        </aside>
    );
}
