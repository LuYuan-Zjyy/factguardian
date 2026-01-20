import React, { useState, useEffect } from 'react';
import { CheckCircle2 } from 'lucide-react';

const FUN_QUOTES = [
    "正在给 DeepSeek 喂电子咖啡...",
    "正在翻阅互联网的每一个角落 (嘘...)",
    "AI 正在进行激烈的哲学思考...",
    "试图分辨 '土豆' 和 '马铃薯' 的区别...",
    "正在与 Redis 进行数据握手...",
    "为了真相，跑断了虚拟的腿...",
    "正在召唤神龙进行校验...",
    "加载中... 请不要关闭浏览器，也不要闭眼...",
    "正在从 1000 万个网页中寻找证据...",
    "事实守护者正在穿梭时空..."
];

const EMOJIS = ['🤖', '🕵️‍♂️', '🦉', '🧠', '🔍'];

// 阶段配置
const STAGE_CONFIG = {
    upload: { label: '上传文档', icon: '📤', color: 'blue' },
    extract_facts: { label: '提取事实', icon: '🔎', color: 'purple' },
    detect_conflicts: { label: '冲突检测', icon: '⚔️', color: 'amber' },
    verify_facts: { label: '事实溯源', icon: '🌐', color: 'green' },
    complete: { label: '完成', icon: '✅', color: 'green' }
};

export default function FunLoading({ 
    progressText,
    // 新增的进度属性
    progress = null  // { stage, stage_label, current, total, progress, message, sub_message, elapsed_seconds, completed_stages }
}) {
    const [quoteIndex, setQuoteIndex] = useState(0);
    const [emojiIndex, setEmojiIndex] = useState(0);

    useEffect(() => {
        // 每 2.5 秒换一句话
        const quoteTimer = setInterval(() => {
            setQuoteIndex(prev => (prev + 1) % FUN_QUOTES.length);
        }, 2500);

        // 每 0.8 秒换一个表情
        const emojiTimer = setInterval(() => {
            setEmojiIndex(prev => (prev + 1) % EMOJIS.length);
        }, 800);

        return () => {
            clearInterval(quoteTimer);
            clearInterval(emojiTimer);
        };
    }, []);

    // 计算真实进度百分比
    const realProgress = progress?.progress || 0;
    const currentStep = progress?.current || 0;
    const totalSteps = progress?.total || 0;
    const currentStage = progress?.stage || 'extract_facts';
    const completedStages = progress?.completed_stages || [];
    const elapsedTime = progress?.elapsed_seconds || 0;

    // 格式化时间
    const formatTime = (seconds) => {
        if (seconds < 60) return `${Math.round(seconds)}秒`;
        const mins = Math.floor(seconds / 60);
        const secs = Math.round(seconds % 60);
        return `${mins}分${secs}秒`;
    };

    // 阶段列表
    const stages = ['extract_facts', 'detect_conflicts', 'verify_facts'];

    return (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-md z-50 flex flex-col items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-lg w-full text-center border-4 border-brand-100 transform transition-all duration-500">
                
                {/* 动画区域 */}
                <div className="relative h-24 mb-4 flex items-center justify-center">
                    {/* 背景装饰光环 */}
                    <div className="absolute w-20 h-20 bg-blue-100 rounded-full animate-ping opacity-20"></div>
                    <div className="absolute w-28 h-28 bg-purple-100 rounded-full animate-ping opacity-10 animation-delay-500"></div>
                    
                    {/* 核心表情 */}
                    <div className="text-7xl animate-bounce filter drop-shadow-lg transform transition-all duration-300">
                        {progress ? STAGE_CONFIG[currentStage]?.icon || EMOJIS[emojiIndex] : EMOJIS[emojiIndex]}
                    </div>
                </div>

                {/* 阶段进度指示器 */}
                <div className="flex justify-center items-center gap-2 mb-6">
                    {stages.map((stage, idx) => {
                        const config = STAGE_CONFIG[stage];
                        const isCompleted = completedStages.includes(stage);
                        const isCurrent = currentStage === stage;
                        
                        return (
                            <React.Fragment key={stage}>
                                <div className={`flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-300
                                    ${isCompleted ? 'bg-green-100 text-green-700' : 
                                      isCurrent ? 'bg-brand-100 text-brand-700 ring-2 ring-brand-300 animate-pulse' : 
                                      'bg-slate-100 text-slate-400'}`}
                                >
                                    {isCompleted ? (
                                        <CheckCircle2 className="w-3.5 h-3.5" />
                                    ) : (
                                        <span>{config.icon}</span>
                                    )}
                                    <span>{config.label}</span>
                                </div>
                                {idx < stages.length - 1 && (
                                    <div className={`w-6 h-0.5 ${isCompleted ? 'bg-green-300' : 'bg-slate-200'}`}></div>
                                )}
                            </React.Fragment>
                        );
                    })}
                </div>

                {/* 核心进度提示 */}
                <h3 className="text-lg font-bold text-slate-800 mb-1 min-h-[1.5rem]">
                    {progress?.message || progressText}
                </h3>
                
                {/* 子消息 */}
                {progress?.sub_message && (
                    <p className="text-sm text-slate-500 mb-3 truncate max-w-full">
                        {progress.sub_message}
                    </p>
                )}

                {/* 真实进度条 */}
                <div className="w-full bg-slate-100 rounded-full h-3 mb-2 overflow-hidden relative">
                    {progress && totalSteps > 0 ? (
                        // 真实进度
                        <div 
                            className="h-full bg-gradient-to-r from-brand-500 to-purple-500 transition-all duration-500 ease-out rounded-full"
                            style={{ width: `${Math.min(realProgress, 100)}%` }}
                        >
                            <div className="absolute inset-0 bg-white/20 animate-shimmer"></div>
                        </div>
                    ) : (
                        // 虚假进度动画（无真实进度时）
                        <div className="h-full bg-gradient-to-r from-brand-400 via-purple-400 to-brand-600 animate-progress w-full origin-left"></div>
                    )}
                </div>

                {/* 进度数字 */}
                {progress && totalSteps > 0 && (
                    <div className="flex justify-between text-xs text-slate-500 mb-4">
                        <span>{currentStep} / {totalSteps}</span>
                        <span>{realProgress.toFixed(1)}%</span>
                        <span>已用时: {formatTime(elapsedTime)}</span>
                    </div>
                )}

                {/* 趣味语录 */}
                <div className="h-8 flex items-center justify-center mt-4">
                    <p className="text-slate-500 text-sm italic font-medium animate-fade-in-up" key={quoteIndex}>
                        "{FUN_QUOTES[quoteIndex]}"
                    </p>
                </div>
            </div>
            
            {/* 底部小提示 */}
            <p className="text-white/80 mt-8 text-sm font-light tracking-wide">
                FactGuardian · 使得事实更清晰
            </p>
        </div>
    );
}
