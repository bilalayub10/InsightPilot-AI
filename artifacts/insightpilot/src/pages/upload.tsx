import { useState, useCallback } from 'react';
import { useLocation } from 'wouter';
import { useAnalyzeDataset } from '@workspace/api-client-react';
import { useAppStore } from '../store';
import { Layout } from '../components/layout';
import { LoadingScreen } from '../components/loading-screen';
import { UploadCloud, FileType, CheckCircle, AlertCircle, FileSpreadsheet, FileText } from 'lucide-react';
import { motion } from 'framer-motion';

interface UploadResult {
  datasetId: string;
  name: string;
  rowCount: number;
  columnCount: number;
  columns: string[];
  fileSizeKb: number;
  fileType: string;
  worksheetName?: string | null;
  domain?: string | null;
}

const SUPPORTED_EXTENSIONS = ['.csv', '.xlsx', '.xls'];

function getFileExtension(filename: string): string {
  return filename.slice(filename.lastIndexOf('.')).toLowerCase();
}

function isSupported(filename: string): boolean {
  return SUPPORTED_EXTENSIONS.includes(getFileExtension(filename));
}

function FileIcon({ fileType }: { fileType?: string }) {
  const isExcel = fileType?.toLowerCase().includes('excel');
  const Icon = isExcel ? FileSpreadsheet : FileText;
  return <Icon className="w-8 h-8" />;
}

export default function UploadPage() {
  const [, setLocation] = useLocation();
  const { setAnalysisResult } = useAppStore();

  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const analyzeMutation = useAnalyzeDataset();

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    setError(null);
    setUploadResult(null);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (isSupported(file.name)) {
        setSelectedFile(file);
      } else {
        setError('Unsupported file type. Please upload a .csv, .xlsx, or .xls file.');
      }
    }
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    setUploadResult(null);
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleClear = () => {
    setSelectedFile(null);
    setUploadResult(null);
    setError(null);
  };

  const handleAnalyze = async () => {
    if (!selectedFile) return;
    setError(null);
    setUploadResult(null);

    try {
      // 1. Upload dataset
      setIsUploading(true);
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('name', selectedFile.name.replace(/\.[^/.]+$/, ''));

      const uploadResp = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!uploadResp.ok) {
        const detail = await uploadResp.json().catch(() => ({}));
        throw new Error(detail?.detail ?? `Upload failed (${uploadResp.status})`);
      }

      const uploadRes: UploadResult = await uploadResp.json();
      setUploadResult(uploadRes);
      setIsUploading(false);

      // 2. Analyze dataset
      const analyzeRes = await analyzeMutation.mutateAsync({
        data: { datasetId: uploadRes.datasetId },
      });

      // 3. Store result & navigate
      setAnalysisResult(analyzeRes);
      setLocation('/dashboard');

    } catch (err) {
      console.error(err);
      setIsUploading(false);
      setError(err instanceof Error ? err.message : 'An error occurred during analysis. Please try again.');
    }
  };

  const isLoading = isUploading || analyzeMutation.isPending;
  const isExcel = selectedFile ? getFileExtension(selectedFile.name) !== '.csv' : false;

  return (
    <Layout>
      <div className="max-w-3xl mx-auto pt-8 md:pt-12">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-foreground mb-2">Upload Dataset</h1>
          <p className="text-muted-foreground">
            Upload a CSV or Excel file and let our AI engine extract the insights.
          </p>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-card border border-border rounded-2xl shadow-sm p-8"
        >
          {/* Drop zone */}
          <div
            className={`relative border-2 border-dashed rounded-xl p-12 text-center transition-all ${
              dragActive
                ? 'border-primary bg-primary/5'
                : selectedFile
                  ? 'border-green-500/50 bg-green-50/50 dark:bg-green-900/10'
                  : 'border-border hover:border-primary/50 hover:bg-accent'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input
              type="file"
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              accept=".csv,.xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
              onChange={handleFileChange}
              data-testid="input-file-upload"
            />

            <div className="flex flex-col items-center justify-center gap-4 pointer-events-none">
              {selectedFile ? (
                <>
                  <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-2 ${
                    isExcel
                      ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400'
                      : 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                  }`}>
                    <FileIcon fileType={isExcel ? 'excel' : 'csv'} />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-foreground">{selectedFile.name}</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      {getFileExtension(selectedFile.name).toUpperCase().replace('.', '')} · {(selectedFile.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-green-600 font-medium mt-2">
                    <CheckCircle className="w-4 h-4" /> Ready for analysis
                  </div>
                </>
              ) : (
                <>
                  <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center text-primary mb-2">
                    <UploadCloud className="w-8 h-8" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-foreground">
                      Click or drag file to this area
                    </h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      Upload a CSV or Excel file (.csv, .xlsx, .xls) up to 50 MB
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Post-upload file summary card */}
          {uploadResult && !isLoading && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-6 p-4 bg-muted/50 border border-border rounded-xl"
            >
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
                File Summary
              </p>
              <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">File Name</span>
                  <span className="font-medium text-foreground truncate max-w-[160px]">{uploadResult.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">File Type</span>
                  <span className="font-medium text-foreground">{uploadResult.fileType}</span>
                </div>
                {uploadResult.worksheetName && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Worksheet</span>
                    <span className="font-medium text-foreground">{uploadResult.worksheetName}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Rows</span>
                  <span className="font-medium text-foreground">{uploadResult.rowCount.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Columns</span>
                  <span className="font-medium text-foreground">{uploadResult.columnCount}</span>
                </div>
                {uploadResult.domain && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Business Domain</span>
                    <span className="font-medium text-foreground">{uploadResult.domain}</span>
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {/* Error banner */}
          {error && (
            <div className="mt-6 flex items-center gap-2 p-4 text-sm text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400 rounded-lg">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Actions */}
          <div className="mt-8 flex justify-end gap-4">
            {selectedFile && (
              <button
                onClick={handleClear}
                className="px-6 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground bg-accent hover:bg-border rounded-lg transition-colors"
                disabled={isLoading}
              >
                Clear
              </button>
            )}
            <button
              onClick={handleAnalyze}
              disabled={!selectedFile || isLoading}
              className={`px-8 py-2.5 text-sm font-semibold rounded-lg shadow-sm transition-all flex items-center gap-2 ${
                selectedFile && !isLoading
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90 hover:shadow'
                  : 'bg-muted text-muted-foreground cursor-not-allowed'
              }`}
              data-testid="button-analyze"
            >
              {isLoading ? (isUploading ? 'Uploading…' : 'Analyzing…') : 'Analyze Dataset'}
            </button>
          </div>
        </motion.div>
      </div>

      {isLoading && (
        <LoadingScreen
          message={
            analyzeMutation.isPending
              ? 'Running AI insight engine…'
              : 'Uploading dataset securely…'
          }
        />
      )}
    </Layout>
  );
}
