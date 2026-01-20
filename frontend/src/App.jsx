import React, { useState } from 'react';
import { Layout, FileText, CheckCircle, Smartphone, Globe, ShieldAlert } from 'lucide-react';
import UploadSection from './components/UploadSection';
import ConflictList from './components/ConflictList';
import VerificationResult from './components/VerificationResult';
import DocumentViewer from './components/DocumentViewer';
import FunLoading from './components/FunLoading';
import { uploadDocument, extractFacts, detectConflicts, verifyFacts } from './api';

function App() {
  const [status, setStatus] = useState('idle'); // idle, uploading, processing, done, error
  const [progressStep, setProgressStep] = useState('');
  const [docId, setDocId] = useState(null);
  const [data, setData] = useState({
    docInfo: null,
    conflicts: [],
    verifications: [],
    stats: {}
  });

  const handleUpload = async (file) => {
    try {
      setStatus('uploading');
      setProgressStep('正在上传并解析文档结构...');
      
      const uploadRes = await uploadDocument(file);
      setDocId(uploadRes.document_id);
      
      // Chain the analysis process
      setStatus('processing');
      
      setProgressStep('正在使用 LLM 提取关键事实 (Entity Extraction)...');
      const factRes = await extractFacts(uploadRes.document_id);
      
      setProgressStep('正在进行全文档逻辑矛盾检测 (Conflict Detection)...');
      const conflictRes = await detectConflicts(uploadRes.document_id);
      
      setProgressStep('正在联网进行事实溯源与校验 (Source Verification)...');
      const verifyRes = await verifyFacts(uploadRes.document_id);

      setData({
        docInfo: uploadRes,
        conflicts: conflictRes.conflicts || [],
        verifications: verifyRes.verifications || [],
        stats: {
          totalFacts: factRes.total_facts,
          conflictCount: conflictRes.conflicts_found,
          verifyFail: verifyRes.statistics?.unsupported || 0
        }
      });
      
      setStatus('done');
    } catch (error) {
      alert('处理失败: ' + (error.response?.data?.detail || error.message));
      setStatus('idle');
    }
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
            <h1 className="text-xl font-bold text-slate-800">FactGuardian <span className="text-slate-400 font-normal text-sm ml-2">长文本“事实卫士”</span></h1>
          </div>
          <div className="flex items-center gap-4 text-sm font-medium text-slate-600">
            <div className="flex items-center gap-1.5">
               <span className={`w-2 h-2 rounded-full ${status === 'processing' ? 'bg-amber-500 animate-pulse' : 'bg-green-500'}`}></span>
               {status === 'processing' ? 'AI 分析中...' : '系统就绪'}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8">
        
        {/* State: IDLE / UPLOADING */}
        {(status === 'idle' || status === 'uploading') && (
          <UploadSection onUpload={handleUpload} isUploading={status === 'uploading'} />
        )}

        {/* State: PROCESSING OVERLAY */}
        {status === 'processing' && (
          <FunLoading progressText={progressStep} />
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
                    <button 
                        onClick={() => { setStatus('idle'); setDocId(null); }}
                        className="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs transition-colors"
                    >
                        重新分析
                    </button>
                  </div>
                </div>

                {/* 2. Conflicts */}
                {data.stats.conflictCount > 0 && (
                   <div id="conflicts">
                      <ConflictList conflicts={data.conflicts} />
                   </div>
                )}
                
                {/* 3. Verifications */}
                <div id="verifications">
                    <VerificationResult verifications={data.verifications} />
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
