import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Layout, FileText, CheckCircle, Smartphone, Globe, ShieldAlert, History, Download, Trash2 } from 'lucide-react';
import UploadSection from './components/UploadSection';
import ConflictList from './components/ConflictList';
import VerificationResult from './components/VerificationResult';
import DocumentViewer from './components/DocumentViewer';
import FunLoading from './components/FunLoading';
import { 
    uploadDocument, 
    extractFacts, 
    detectConflicts, 
    verifyFacts,
    subscribeProgress,
    saveToHistory,
    getHistory,
    deleteFromHistory,
    exportReport
} from './api';

function App() {
  const [status, setStatus] = useState('idle'); // idle, uploading, processing, done, error
  const [progressStep, setProgressStep] = useState('');
  const [progress, setProgress] = useState(null); // SSE 进度数据
  const [docId, setDocId] = useState(null);
  const [data, setData] = useState({
    docInfo: null,
    conflicts: [],
    verifications: [],
    stats: {}
  });
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistoryState] = useState([]);
  
  // 用于跳转高亮的 ref
  const conflictRefs = useRef({});
  const verificationRefs = useRef({});
  
  // 取消订阅函数
  const unsubscribeRef = useRef(null);

  // 加载历史记录
  useEffect(() => {
    setHistoryState(getHistory());
  }, []);

  // 处理高亮点击跳转
  const handleHighlightClick = useCallback((type, id) => {
    // type: 'conflict' 或 'verification'
    // id: 对应的 conflict_id 或 fact_id
    const targetRef = type === 'conflict' ? conflictRefs.current[id] : verificationRefs.current[id];
    
    if (targetRef) {
      targetRef.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // 添加高亮动画
      targetRef.classList.add('ring-4', 'ring-brand-400', 'ring-opacity-75');
      setTimeout(() => {
        targetRef.classList.remove('ring-4', 'ring-brand-400', 'ring-opacity-75');
      }, 2000);
    }
  }, []);

  const handleUpload = async (file) => {
    try {
      setStatus('uploading');
      setProgressStep('正在上传并解析文档结构...');
      setProgress(null);
      
      const uploadRes = await uploadDocument(file);
      setDocId(uploadRes.document_id);
      
      // Chain the analysis process
      setStatus('processing');
      
      // 订阅进度更新
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
      }
      
      unsubscribeRef.current = subscribeProgress(
        uploadRes.document_id,
        (progressData) => {
          setProgress(progressData);
          setProgressStep(progressData.message);
        },
        (error) => {
          console.error('进度订阅错误:', error);
        }
      );
      
      setProgressStep('正在使用 LLM 提取关键事实 (Entity Extraction)...');
      const factRes = await extractFacts(uploadRes.document_id);
      
      setProgressStep('正在进行全文档逻辑矛盾检测 (Conflict Detection)...');
      const conflictRes = await detectConflicts(uploadRes.document_id);
      
      setProgressStep('正在联网进行事实溯源与校验 (Source Verification)...');
      const verifyRes = await verifyFacts(uploadRes.document_id);

      const resultData = {
        docInfo: uploadRes,
        conflicts: conflictRes.conflicts || [],
        verifications: verifyRes.verifications || [],
        stats: {
          totalFacts: factRes.total_facts,
          conflictCount: conflictRes.conflicts_found,
          verifyFail: verifyRes.statistics?.unsupported || 0
        }
      };
      
      setData(resultData);
      
      // 保存到历史记录
      saveToHistory(resultData);
      setHistoryState(getHistory());
      
      // 取消订阅
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }
      
      setStatus('done');
      setProgress(null);
    } catch (error) {
      alert('处理失败: ' + (error.response?.data?.detail || error.message));
      setStatus('idle');
      setProgress(null);
      
      if (unsubscribeRef.current) {
        unsubscribeRef.current();
        unsubscribeRef.current = null;
      }
    }
  };

  // 从历史记录恢复
  const handleRestoreHistory = (record) => {
    setData({
      docInfo: { 
        document_id: record.documentId, 
        filename: record.filename,
        sections: [] // 历史记录不保存完整文档内容
      },
      conflicts: record.conflicts || [],
      verifications: record.verifications || [],
      stats: record.stats || {}
    });
    setDocId(record.documentId);
    setStatus('done');
    setShowHistory(false);
  };

  // 删除历史记录
  const handleDeleteHistory = (id, e) => {
    e.stopPropagation();
    const updated = deleteFromHistory(id);
    setHistoryState(updated);
  };

  // 导出报告
  const handleExport = () => {
    exportReport(data, data.docInfo?.filename || 'document');
  };

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-brand-600 text-white p-1.5 rounded-lg">
              <ShieldAlert size={24} />
            </div>
            <h1 className="text-xl font-bold text-slate-800">FactGuardian <span className="text-slate-400 font-normal text-sm ml-2">长文本"事实卫士"</span></h1>
          </div>
          <div className="flex items-center gap-4 text-sm font-medium text-slate-600">
            {/* 历史记录按钮 */}
            <button 
              onClick={() => setShowHistory(!showHistory)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors"
            >
              <History size={18} />
              <span>历史记录</span>
              {history.length > 0 && (
                <span className="bg-brand-100 text-brand-700 text-xs px-1.5 py-0.5 rounded-full">{history.length}</span>
              )}
            </button>
            
            <div className="flex items-center gap-1.5">
               <span className={`w-2 h-2 rounded-full ${status === 'processing' ? 'bg-amber-500 animate-pulse' : 'bg-green-500'}`}></span>
               {status === 'processing' ? 'AI 分析中...' : '系统就绪'}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8">
        
        {/* 历史记录面板 */}
        {showHistory && (
          <div className="mb-6 card animate-in fade-in slide-in-from-top-2 duration-300">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold flex items-center gap-2">
                <History className="text-brand-600" />
                历史分析记录
              </h3>
              <button 
                onClick={() => setShowHistory(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                ✕
              </button>
            </div>
            
            {history.length === 0 ? (
              <p className="text-slate-500 text-center py-8">暂无历史记录</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {history.map((record) => (
                  <div 
                    key={record.id}
                    onClick={() => handleRestoreHistory(record)}
                    className="flex items-center justify-between p-3 bg-slate-50 rounded-lg hover:bg-slate-100 cursor-pointer transition-colors group"
                  >
                    <div className="flex-1">
                      <div className="font-medium text-slate-800">{record.filename}</div>
                      <div className="text-xs text-slate-500">
                        {new Date(record.timestamp).toLocaleString('zh-CN')}
                        <span className="mx-2">·</span>
                        {record.stats?.totalFacts || 0} 条事实
                        <span className="mx-2">·</span>
                        <span className={record.stats?.conflictCount > 0 ? 'text-amber-600' : 'text-green-600'}>
                          {record.stats?.conflictCount || 0} 冲突
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={(e) => handleDeleteHistory(record.id, e)}
                      className="opacity-0 group-hover:opacity-100 p-1.5 text-slate-400 hover:text-red-500 transition-all"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        
        {/* State: IDLE / UPLOADING */}
        {(status === 'idle' || status === 'uploading') && (
          <UploadSection onUpload={handleUpload} isUploading={status === 'uploading'} />
        )}

        {/* State: PROCESSING OVERLAY */}
        {status === 'processing' && (
          <FunLoading progressText={progressStep} progress={progress} />
        )}

        {/* State: RESULTS DASHBOARD */}
        {status === 'done' && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Stats Overview */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="card border-l-4 border-l-blue-500">
                <div className="text-slate-500 text-sm font-medium uppercase tracking-wider">提取事实</div>
                <div className="text-3xl font-bold text-slate-800 mt-1">{data.stats.totalFacts}</div>
                <div className="text-xs text-slate-400 mt-2">自 {data.docInfo.filename}</div>
              </div>
              <div className={`card border-l-4 ${data.stats.conflictCount > 0 ? 'border-l-amber-500' : 'border-l-green-500'}`}>
                <div className="text-slate-500 text-sm font-medium uppercase tracking-wider">冲突矛盾</div>
                <div className="text-3xl font-bold text-slate-800 mt-1">{data.stats.conflictCount}</div>
                <div className="text-xs text-slate-400 mt-2">{data.stats.conflictCount > 0 ? '需人工复核' : '全文档一致'}</div>
              </div>
              <div className={`card border-l-4 ${data.stats.verifyFail > 0 ? 'border-l-red-500' : 'border-l-green-500'}`}>
                <div className="text-slate-500 text-sm font-medium uppercase tracking-wider">事实谬误</div>
                <div className="text-3xl font-bold text-slate-800 mt-1">{data.stats.verifyFail}</div>
                <div className="text-xs text-slate-400 mt-2">联网查证发现错误</div>
              </div>
            </div>

            {/* Main Content Area - Split View */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 h-full">
              
              {/* Left Column: Document Viewer (Sticky) */}
              <div className="xl:sticky xl:top-24 h-fit min-h-[500px]">
                <DocumentViewer 
                    sections={data.docInfo.sections} 
                    conflicts={data.conflicts}
                    verifications={data.verifications}
                    onHighlightClick={handleHighlightClick}
                />
              </div>

              {/* Right Column: Analysis Results */}
              <div className="space-y-8 pb-10">
                
                {/* 1. Doc Overview Card */}
                <div className="card bg-slate-800 text-white border-transparent">
                  <div className="flex justify-between items-start">
                    <div>
                        <h3 className="font-bold flex items-center gap-2 mb-2">
                            <FileText size={18} /> 文档分析概览
                        </h3>
                        <p className="text-slate-400 text-sm">{data.docInfo.filename}</p>
                    </div>
                    <div className="flex gap-2">
                      <button 
                          onClick={handleExport}
                          className="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs transition-colors flex items-center gap-1"
                      >
                          <Download size={14} />
                          导出报告
                      </button>
                      <button 
                          onClick={() => { setStatus('idle'); setDocId(null); }}
                          className="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs transition-colors"
                      >
                          重新分析
                      </button>
                    </div>
                  </div>
                </div>

                {/* 2. Conflicts */}
                {data.stats.conflictCount > 0 && (
                   <div id="conflicts">
                      <ConflictList 
                        conflicts={data.conflicts} 
                        conflictRefs={conflictRefs}
                      />
                   </div>
                )}
                
                {/* 3. Verifications */}
                <div id="verifications">
                    <VerificationResult 
                      verifications={data.verifications}
                      verificationRefs={verificationRefs}
                    />
                </div>
              </div>

            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
