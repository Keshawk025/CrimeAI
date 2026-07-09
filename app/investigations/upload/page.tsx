"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { Button } from "@/components/ui/button";
import {
  UploadCloud,
  FileText,
  Trash2,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Calendar,
  Search,
  ArrowLeft,
  FileCode,
  FileEdit,
  Brain,
  Copy,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Tags,
  Database,
  FileSearch,
  Check,
  MessageSquare,
  Bot,
  Send,
  ShieldAlert,
  Cpu,
  Lightbulb,
  Eye,
  Shield,
  Info,
} from "lucide-react";

// --- Explainability Panel Component ---
interface ExplainabilityData {
  confidence: number;
  reasoning: string;
  supporting_cases: string[];
  supporting_entities: string[];
  limitations: string[];
}

function ExplainabilityPanel({ data }: { data: ExplainabilityData | null }) {
  if (!data) return null;
  const confColor =
    data.confidence >= 80
      ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
      : data.confidence >= 50
      ? "text-amber-400 bg-amber-500/10 border-amber-500/20"
      : "text-red-400 bg-red-500/10 border-red-500/20";

  return (
    <details className="group rounded-xl border border-indigo-500/15 bg-indigo-950/10 overflow-hidden transition-all">
      <summary className="flex items-center justify-between px-4 py-3 cursor-pointer select-none hover:bg-indigo-950/20 transition-colors">
        <div className="flex items-center gap-2">
          <span className="p-1 rounded bg-indigo-500/10 text-indigo-400">
            <Eye size={12} />
          </span>
          <span className="text-xs font-bold text-indigo-300">Explainability &amp; Evidence Chain</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold border ${confColor}`}>
            {data.confidence}% confidence
          </span>
          <ChevronDown size={14} className="text-indigo-400/60 group-open:rotate-180 transition-transform" />
        </div>
      </summary>
      <div className="px-4 pb-4 pt-1 space-y-3 animate-in fade-in duration-200">
        {/* Reasoning */}
        <div className="space-y-1">
          <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 flex items-center gap-1">
            <Brain size={10} /> Reasoning
          </p>
          <p className="text-xs text-zinc-300 leading-relaxed bg-white/[0.02] rounded-lg border border-white/[0.04] px-3 py-2">
            {data.reasoning}
          </p>
        </div>

        {/* Supporting Entities */}
        {data.supporting_entities.length > 0 && (
          <div className="space-y-1">
            <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 flex items-center gap-1">
              <Tags size={10} /> Supporting Entities ({data.supporting_entities.length})
            </p>
            <div className="flex flex-wrap gap-1">
              {data.supporting_entities.map((ent, i) => (
                <span key={i} className="inline-flex items-center rounded bg-indigo-500/8 px-1.5 py-0.5 text-[9px] text-indigo-300 border border-indigo-500/15 font-mono">
                  {ent}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Supporting Cases */}
        {data.supporting_cases.length > 0 && (
          <div className="space-y-1">
            <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 flex items-center gap-1">
              <FileSearch size={10} /> Supporting Cases ({data.supporting_cases.length})
            </p>
            <div className="flex flex-wrap gap-1">
              {data.supporting_cases.map((c, i) => (
                <span key={i} className="inline-flex items-center rounded bg-sky-500/8 px-1.5 py-0.5 text-[9px] text-sky-300 border border-sky-500/15 font-mono">
                  {c}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Limitations */}
        {data.limitations.length > 0 && (
          <div className="space-y-1">
            <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 flex items-center gap-1">
              <Shield size={10} /> Limitations
            </p>
            <div className="space-y-1">
              {data.limitations.map((lim, i) => (
                <div key={i} className="flex items-start gap-1.5 text-[11px] text-amber-300/80">
                  <AlertCircle size={10} className="mt-0.5 shrink-0 text-amber-500/60" />
                  <span>{lim}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </details>
  );
}

// --- API configuration ---
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

interface FIREmbeddingItem {
  id: string;
  fir_id: string;
  qdrant_point_id: string;
  embedding_model: string;
  vector_dimension: number;
  indexed_at: string;
}

interface FIRItem {
  id: string;
  case_number: string;
  original_filename: string;
  file_type: "pdf" | "docx" | "txt";
  file_size: number;
  status: string;
  created_by: string;
  uploaded_at: string;
  embedding?: FIREmbeddingItem;
}

interface ToastMessage {
  id: string;
  type: "success" | "error" | "info";
  title: string;
  message: string;
}

const getStatusBadge = (status: string) => {
  switch (status?.toLowerCase()) {
    case "uploaded":
      return {
        label: "Uploaded",
        className: "bg-slate-500/10 text-slate-400 border-slate-500/20",
      };
    case "text_extracted":
      return {
        label: "Text Extracted",
        className: "bg-sky-500/10 text-sky-400 border-sky-500/20",
      };
    case "entities_extracted":
      return {
        label: "Entities Extracted",
        className: "bg-amber-500/10 text-amber-400 border-amber-500/20",
      };
    case "indexed":
      return {
        label: "Indexed",
        className: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
      };
    case "ready_for_investigation":
      return {
        label: "Ready for AI",
        className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 animate-pulse font-semibold",
      };
    case "failed":
      return {
        label: "Failed",
        className: "bg-rose-500/10 text-rose-400 border-rose-500/20",
      };
    default:
      return {
        label: status || "Unknown",
        className: "bg-gray-500/10 text-gray-400 border-gray-500/20",
      };
  }
};

export default function UploadPage() {
  const [firs, setFirs] = useState<FIRItem[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [caseNumber, setCaseNumber] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- Extraction States ---
  const [extractingId, setExtractingId] = useState<string | null>(null);
  const [selectedExtraction, setSelectedExtraction] = useState<any | null>(null);
  const [isExtractionModalOpen, setIsExtractionModalOpen] = useState(false);

  // --- Entity Extraction States ---
  const [extractingEntitiesId, setExtractingEntitiesId] = useState<string | null>(null);
  const [selectedEntities, setSelectedEntities] = useState<any[] | null>(null);
  const [isEntitiesModalOpen, setIsEntitiesModalOpen] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({});
  const [activeEntityFirId, setActiveEntityFirId] = useState<string | null>(null);
  const [entitiesExplainability, setEntitiesExplainability] = useState<ExplainabilityData | null>(null);

  // --- Embedding / Indexing States ---
  const [indexingId, setIndexingId] = useState<string | null>(null);

  // --- Similar Cases States ---
  const [searchingSimilarId, setSearchingSimilarId] = useState<string | null>(null);
  const [similarCases, setSimilarCases] = useState<any | null>(null);
  const [isSimilarModalOpen, setIsSimilarModalOpen] = useState(false);
  const [similarExplainability, setSimilarExplainability] = useState<ExplainabilityData | null>(null);

  // --- Copilot States ---
  const [isCopilotOpen, setIsCopilotOpen] = useState(false);
  const [copilotFir, setCopilotFir] = useState<FIRItem | null>(null);
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isCopilotTyping, setIsCopilotTyping] = useState(false);

  // --- Recommendations States ---
  const [isRecommendationsOpen, setIsRecommendationsOpen] = useState(false);
  const [recommendationsFir, setRecommendationsFir] = useState<FIRItem | null>(null);
  const [recommendations, setRecommendations] = useState<any[] | null>(null);
  const [loadingRecommendations, setLoadingRecommendations] = useState(false);
  const [recommendationsError, setRecommendationsError] = useState<string | null>(null);
  const [completedRecommendations, setCompletedRecommendations] = useState<string[]>([]);
  const [recommendationsFilter, setRecommendationsFilter] = useState("All");
  const [recommendationsExplainability, setRecommendationsExplainability] = useState<ExplainabilityData | null>(null);

  // --- Fetch FIRs ---
  const fetchFIRs = async () => {
    setLoadingList(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/firs?limit=100`);
      if (res.ok) {
        const data = await res.json();
        setFirs(data.items || []);
      } else {
        showToast("error", "Error", "Failed to fetch uploaded FIRs.");
      }
    } catch (err) {
      console.error(err);
      showToast("error", "Network Error", "Unable to connect to the backend server.");
    } finally {
      setLoadingList(false);
    }
  };

  useEffect(() => {
    fetchFIRs();
  }, []);

  // --- Extract Text ---
  const handleExtract = async (id: string) => {
    setExtractingId(id);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/firs/${id}/extract`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setSelectedExtraction(data);
        setIsExtractionModalOpen(true);
        showToast("success", "Extraction Complete", "Text and statistics extracted successfully.");
      } else {
        const errorData = await res.json();
        showToast("error", "Extraction Failed", errorData.detail || "Unable to extract text from this document.");
      }
    } catch (err) {
      console.error(err);
      showToast("error", "Network Error", "Unable to connect to the backend server.");
    } finally {
      setExtractingId(null);
    }
  };

  // --- Extract Entities ---
  const handleExtractEntities = async (id: string) => {
    setExtractingEntitiesId(id);
    setActiveEntityFirId(id);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/firs/${id}/entities`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        // The API now returns an explainability wrapper: { result, confidence, reasoning, ... }
        const entityList = data.result || data;
        const explainability: ExplainabilityData = {
          confidence: data.confidence ?? 100,
          reasoning: data.reasoning || "",
          supporting_cases: data.supporting_cases || [],
          supporting_entities: data.supporting_entities || [],
          limitations: data.limitations || [],
        };
        setSelectedEntities(entityList);
        setEntitiesExplainability(explainability);
        setIsEntitiesModalOpen(true);
        // Initialize all categories as expanded by default
        const initialExpanded: Record<string, boolean> = {};
        (Array.isArray(entityList) ? entityList : []).forEach((entity: any) => {
          initialExpanded[entity.entity_type] = true;
        });
        setExpandedCategories(initialExpanded);
        showToast("success", "Entities Extracted", "AI Entity Extraction completed successfully.");
      } else {
        const errorData = await res.json();
        showToast("error", "Extraction Failed", errorData.detail || "Unable to extract entities. Make sure text is extracted first.");
      }
    } catch (err) {
      console.error(err);
      showToast("error", "Network Error", "Unable to connect to the backend server.");
    } finally {
      setExtractingEntitiesId(null);
    }
  };

  // --- Index FIR ---
  const handleIndexFIR = async (id: string) => {
    setIndexingId(id);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/firs/${id}/index`, {
        method: "POST",
      });
      if (res.ok) {
        showToast("success", "Indexing Complete", "FIR successfully embedded and indexed in Qdrant.");
        fetchFIRs();
      } else {
        const errorData = await res.json();
        showToast("error", "Indexing Failed", errorData.detail || "Unable to index this document. Make sure text is extracted first.");
      }
    } catch (err) {
      console.error(err);
      showToast("error", "Network Error", "Unable to connect to the backend server.");
    } finally {
      setIndexingId(null);
    }
  };

  // --- Find Similar Cases ---
  const handleFindSimilar = async (firId: string) => {
    setSearchingSimilarId(firId);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/firs/${firId}/similar`, {
        method: "POST",
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to find similar cases.");
      }
      const data = await res.json();
      setSimilarCases(data);
      setSimilarExplainability({
        confidence: data.confidence ?? 80,
        reasoning: data.reasoning || "",
        supporting_cases: data.supporting_cases || [],
        supporting_entities: data.supporting_entities || [],
        limitations: data.limitations || [],
      });
      setIsSimilarModalOpen(true);
      showToast("success", "Similar Cases Found", "Retrieved similar historical cases successfully.");
    } catch (err: any) {
      console.error(err);
      showToast("error", "Query Failed", err.message || "Failed to query similar cases.");
    } finally {
      setSearchingSimilarId(null);
    }
  };

  // --- Copilot Handlers ---
  const handleOpenCopilot = (fir: FIRItem) => {
    setCopilotFir(fir);
    setChatHistory([
      {
        sender: "copilot",
        text: `Hello! I am your AI Investigation Copilot. I have analyzed case ${fir.case_number}. How can I assist you today?`,
      },
    ]);
    setIsCopilotOpen(true);
  };

  const handleSendCopilotMessage = async (msgText: string) => {
    if (!msgText.trim() || !copilotFir) return;

    const userMsg = { sender: "user", text: msgText };
    setChatHistory((prev) => [...prev, userMsg]);
    setInputMessage("");
    setIsCopilotTyping(true);

    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/firs/${copilotFir.id}/copilot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: msgText }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to get answer from copilot.");
      }

      const data = await res.json();
      setChatHistory((prev) => [
        ...prev,
        {
          sender: "copilot",
          text: data.answer || data.result,
          confidence: data.confidence,
          reasoning: data.reasoning,
          sources: data.sources,
          workflowSteps: data.workflow_steps,
          supporting_entities: data.supporting_entities || [],
          supporting_cases: data.supporting_cases || [],
          limitations: data.limitations || [],
        },
      ]);
    } catch (err: any) {
      console.error(err);
      setChatHistory((prev) => [
        ...prev,
        {
          sender: "copilot",
          text: `Error: ${err.message || "Unable to reach the copilot service."}`,
          isError: true,
        },
      ]);
    } finally {
      setIsCopilotTyping(false);
    }
  };

  const handleFetchRecommendations = async (fir: FIRItem) => {
    setRecommendationsFir(fir);
    setIsRecommendationsOpen(true);
    setRecommendations(null);
    setRecommendationsError(null);
    setLoadingRecommendations(true);

    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/firs/${fir.id}/recommendations`, {
        method: "POST",
      });

      if (!res.ok) {
        const errData = await res.json();
        if (res.status === 400 && errData.detail?.includes("blocked")) {
          throw new Error("Request blocked by AI safety policy. " + (errData.detail || ""));
        }
        throw new Error(errData.detail || "Failed to load next investigation steps.");
      }

      const data = await res.json();
      setRecommendationsExplainability({
        confidence: data.confidence ?? 80,
        reasoning: data.reasoning || "",
        supporting_cases: data.supporting_cases || [],
        supporting_entities: data.supporting_entities || [],
        limitations: data.limitations || [],
      });
      if (data.message && (!data.recommendations || data.recommendations.length === 0)) {
        setRecommendationsError(data.message);
      } else {
        setRecommendations(data.recommendations || []);
      }
    } catch (err: any) {
      console.error(err);
      setRecommendationsError(err.message || "Failed to retrieve recommendations.");
    } finally {
      setLoadingRecommendations(false);
    }
  };



  // --- Toast Manager ---
  const showToast = (type: "success" | "error" | "info", title: string, message: string) => {
    const newToast: ToastMessage = {
      id: Math.random().toString(36).substring(2, 9),
      type,
      title,
      message,
    };
    setToasts((prev) => [...prev, newToast]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== newToast.id));
    }, 5000);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // --- File validation and handling ---
  const handleFileChange = (file: File | null) => {
    if (!file) {
      setSelectedFile(null);
      return;
    }

    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    const allowedExtensions = [".pdf", ".docx", ".txt"];
    const allowedMimeTypes = [
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "text/plain",
    ];

    // File type validation
    if (!allowedExtensions.includes(ext) && !allowedMimeTypes.includes(file.type)) {
      showToast("error", "Invalid File Type", "Only PDF, DOCX, and TXT files are accepted.");
      setSelectedFile(null);
      return;
    }

    // Size validation: 20 MB limit
    const maxSize = 20 * 1024 * 1024;
    if (file.size > maxSize) {
      showToast("error", "File Too Large", "Maximum allowed file size is 20 MB.");
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
    showToast("info", "File Selected", `Ready to upload: ${file.name}`);
  };

  // --- Drag and Drop handlers ---
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  // --- Upload FIR ---
  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      showToast("error", "No File", "Please select a file to upload.");
      return;
    }
    if (!caseNumber.trim()) {
      showToast("error", "Missing Case Number", "Please specify a valid Case Number.");
      return;
    }

    setUploading(true);
    setUploadProgress(10); // Start with a small progress indication

    // Duplicate detection client-side
    const duplicate = firs.some(
      (f) => f.case_number === caseNumber.trim() && f.original_filename === selectedFile.name
    );
    if (duplicate) {
      showToast("error", "Duplicate File", "This file has already been uploaded for this case.");
      setUploading(false);
      setUploadProgress(null);
      return;
    }

    // Simulate progress updates for a smoother user experience
    const progressInterval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev === null) return null;
        if (prev >= 90) {
          clearInterval(progressInterval);
          return 90;
        }
        return prev + 15;
      });
    }, 200);

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("case_number", caseNumber.trim());
    formData.append("created_by", "system");

    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/firs/upload`, {
        method: "POST",
        body: formData,
      });

      clearInterval(progressInterval);

      if (res.status === 201 || res.status === 200) {
        setUploadProgress(100);
        showToast("success", "Success", "FIR uploaded and metadata saved successfully.");
        setCaseNumber("");
        setSelectedFile(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
        
        // Refresh the list
        fetchFIRs();
      } else {
        const errorData = await res.json();
        showToast(
          "error",
          "Upload Failed",
          errorData.detail || "Server rejected the upload file."
        );
      }
    } catch (err) {
      console.error(err);
      showToast("error", "Upload Failed", "Network error occurred during file upload.");
    } finally {
      setTimeout(() => {
        setUploading(false);
        setUploadProgress(null);
      }, 500);
    }
  };

  // --- Delete FIR ---
  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this FIR and its file?")) return;

    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/firs/${id}`, {
        method: "DELETE",
      });

      if (res.ok) {
        showToast("success", "Deleted", "FIR has been deleted successfully.");
        // Refresh list
        fetchFIRs();
      } else {
        showToast("error", "Delete Failed", "Failed to delete the selected FIR.");
      }
    } catch (err) {
      console.error(err);
      showToast("error", "Error", "Unable to connect to the server to delete the file.");
    }
  };

  // --- Helper: format file size ---
  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  // --- Filtered FIRs ---
  const filteredFirs = firs.filter((fir) => {
    const search = searchQuery.toLowerCase();
    return (
      fir.case_number.toLowerCase().includes(search) ||
      fir.original_filename.toLowerCase().includes(search)
    );
  });

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground gradient-hero">
      <Navbar />

      <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-12">
        {/* Back Link */}
        <div className="mb-8">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft size={16} />
            Back to Dashboard
          </Link>
        </div>

        {/* Page Header */}
        <div className="mb-10 text-left">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
            FIR Upload &amp; <span className="text-gradient-brand">Management</span>
          </h1>
          <p className="mt-2 text-base text-muted-foreground max-w-2xl">
            Upload official First Information Reports (FIRs) to the secure storage environment. Supported formats include PDF, DOCX, and TXT (Max size 20 MB).
          </p>
        </div>

        <div className="grid grid-cols-1 gap-10 lg:grid-cols-3">
          {/* Left Column: Upload Form */}
          <div className="lg:col-span-1">
            <div className="card-glass rounded-2xl p-6 border border-white/[0.08]">
              <h2 className="text-lg font-bold mb-5 flex items-center gap-2">
                <FileEdit size={18} className="text-primary" />
                Upload New Document
              </h2>

              <form onSubmit={handleUpload} className="space-y-5">
                {/* Case Number Input */}
                <div>
                  <label htmlFor="case-number" className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                    Case / FIR Number <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    id="case-number"
                    required
                    placeholder="e.g. FIR/2026/0894"
                    value={caseNumber}
                    onChange={(e) => setCaseNumber(e.target.value)}
                    disabled={uploading}
                    className="w-full rounded-lg border border-white/[0.08] bg-white/[0.02] px-3.5 py-2 text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground/50 focus:border-primary/50 focus:ring-2 focus:ring-primary/20"
                  />
                </div>

                {/* Drag and Drop Zone */}
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                    FIR File <span className="text-red-500">*</span>
                  </label>
                  <div
                    onDragEnter={handleDrag}
                    onDragOver={handleDrag}
                    onDragLeave={handleDrag}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className={`relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-8 text-center cursor-pointer transition-all duration-200 ${
                      dragActive
                        ? "border-primary bg-primary/[0.04]"
                        : selectedFile
                        ? "border-emerald-500/50 bg-emerald-500/[0.02]"
                        : "border-white/[0.08] hover:border-white/[0.16] bg-white/[0.01]"
                    }`}
                  >
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
                      className="hidden"
                      accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
                      disabled={uploading}
                    />

                    {selectedFile ? (
                      <div className="flex flex-col items-center">
                        <div className="rounded-full bg-emerald-500/10 p-3 text-emerald-400 mb-3 animate-pulse">
                          <FileText size={28} />
                        </div>
                        <p className="text-sm font-semibold text-foreground max-w-full truncate px-4">
                          {selectedFile.name}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {formatBytes(selectedFile.size)}
                        </p>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedFile(null);
                            if (fileInputRef.current) fileInputRef.current.value = "";
                          }}
                          className="mt-3 text-xs text-red-400 hover:text-red-300 underline font-medium transition-colors"
                        >
                          Remove file
                        </button>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center">
                        <div className="rounded-full bg-primary/10 p-3 text-primary mb-3">
                          <UploadCloud size={28} />
                        </div>
                        <p className="text-sm font-medium text-foreground">
                          Drag and drop file here, or{" "}
                          <span className="text-primary hover:underline">browse</span>
                        </p>
                        <p className="text-xs text-muted-foreground mt-2">
                          Supports PDF, DOCX, TXT up to 20 MB
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Progress bar */}
                {uploading && uploadProgress !== null && (
                  <div className="w-full space-y-1.5">
                    <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
                      <span className="flex items-center gap-1.5">
                        <Loader2 size={12} className="animate-spin text-primary" />
                        Uploading to secure storage...
                      </span>
                      <span>{uploadProgress}%</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-white/[0.04] overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-primary to-rose-500 transition-all duration-300 rounded-full"
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Submit button */}
                <Button
                  type="submit"
                  disabled={uploading || !selectedFile || !caseNumber.trim()}
                  className="w-full gradient-brand py-5 text-white font-semibold shadow-lg transition-transform hover:scale-[1.02] hover:opacity-90 disabled:scale-100"
                >
                  {uploading ? (
                    <>
                      <Loader2 size={16} className="mr-2 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    "Save FIR Document"
                  )}
                </Button>
              </form>
            </div>
          </div>

          {/* Right Column: Files Management Table */}
          <div className="lg:col-span-2 space-y-6">
            <div className="card-glass rounded-2xl p-6 border border-white/[0.08] flex flex-col h-full">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
                <h2 className="text-lg font-bold flex items-center gap-2">
                  <FileCode size={18} className="text-primary" />
                  Uploaded FIR Documents
                </h2>

                {/* Search Bar */}
                <div className="relative w-full sm:w-64">
                  <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground/60" />
                  <input
                    type="text"
                    placeholder="Search by Case or Filename"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full rounded-lg border border-white/[0.08] bg-white/[0.02] pl-9 pr-3.5 py-1.5 text-xs text-foreground outline-none transition-all focus:border-primary/50 focus:ring-1 focus:ring-primary/20"
                  />
                </div>
              </div>

              {/* Table / List */}
              <div className="flex-1 overflow-x-auto min-h-[300px]">
                {loadingList ? (
                  <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
                    <Loader2 size={32} className="animate-spin text-primary mb-3" />
                    <p className="text-sm font-medium">Loading FIR inventory...</p>
                  </div>
                ) : filteredFirs.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-20 text-center text-muted-foreground">
                    <FileText size={40} className="text-muted-foreground/20 mb-3" />
                    <p className="text-sm font-semibold">No FIR documents found</p>
                    <p className="text-xs text-muted-foreground/80 mt-1 max-w-xs">
                      {searchQuery ? "No matches found. Try adjusting your search query." : "Upload your first FIR document to get started."}
                    </p>
                  </div>
                ) : (
                  <table className="min-w-[1000px] w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-white/[0.06] text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                        <th className="pb-3 pr-4 font-semibold">Case Number</th>
                        <th className="pb-3 pr-4 font-semibold">File Name</th>
                        <th className="pb-3 pr-4 font-semibold">Type</th>
                        <th className="pb-3 pr-4 font-semibold text-right">Size</th>
                        <th className="pb-3 pr-4 font-semibold text-center">Status</th>
                        <th className="pb-3 pr-4 font-semibold text-center">Uploaded At</th>
                        <th className="pb-3 text-right w-[280px] min-w-[280px] font-semibold">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.04] text-sm">
                      {filteredFirs.map((fir) => (
                        <tr key={fir.id} className="hover:bg-white/[0.01] transition-colors group">
                          {/* Case Number */}
                          <td className="py-3.5 pr-4 font-semibold text-foreground">
                            {fir.case_number}
                          </td>
                          {/* File Name */}
                          <td className="py-3.5 pr-4 max-w-[200px] truncate text-muted-foreground group-hover:text-foreground transition-colors" title={fir.original_filename}>
                            <div className="font-semibold text-foreground">{fir.original_filename}</div>
                            {fir.embedding ? (
                              <div className="text-[10px] text-indigo-400 font-mono mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5">
                                <span className="font-bold">✓ Indexed</span>
                                <span className="w-1 h-1 rounded-full bg-indigo-500/30" />
                                <span>Dim: {fir.embedding.vector_dimension}</span>
                                <span className="w-1 h-1 rounded-full bg-indigo-500/30" />
                                <span>Model: {fir.embedding.embedding_model.replace("models/", "")}</span>
                                <span className="w-1 h-1 rounded-full bg-indigo-500/30" />
                                <span>Time: {new Date(fir.embedding.indexed_at).toLocaleTimeString()}</span>
                              </div>
                            ) : (
                              <div className="text-[10px] text-muted-foreground/60 mt-1">
                                • Not Indexed
                              </div>
                            )}
                          </td>
                          {/* Type */}
                          <td className="py-3.5 pr-4">
                            <span className="inline-flex items-center rounded bg-white/[0.04] px-1.5 py-0.5 text-xs font-medium uppercase text-muted-foreground border border-white/[0.06]">
                              {fir.file_type}
                            </span>
                          </td>
                          {/* Size */}
                          <td className="py-3.5 pr-4 text-right text-xs text-muted-foreground font-mono">
                            {formatBytes(fir.file_size)}
                          </td>
                          {/* Status */}
                          <td className="py-3.5 pr-4 text-center">
                            {(() => {
                              const badge = getStatusBadge(fir.status);
                              return (
                                <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium border ${badge.className}`}>
                                  {badge.label}
                                </span>
                              );
                            })()}
                          </td>
                          {/* Uploaded At */}
                          <td className="py-3.5 pr-4 text-center text-xs text-muted-foreground">
                            <div className="flex items-center justify-center gap-1">
                              <Calendar size={12} className="text-muted-foreground/60" />
                              {new Date(fir.uploaded_at).toLocaleDateString(undefined, {
                                month: "short",
                                day: "numeric",
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </div>
                          </td>
                          {/* Actions */}
                          <td className="py-3.5 text-right w-[280px] min-w-[280px]">
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                onClick={() => handleExtract(fir.id)}
                                disabled={extractingId !== null || extractingEntitiesId !== null || indexingId !== null}
                                className="text-muted-foreground hover:text-primary p-1.5 rounded-lg hover:bg-primary/10 transition-all flex items-center justify-center disabled:opacity-50"
                                title="Extract Text"
                              >
                                {extractingId === fir.id ? (
                                  <Loader2 size={15} className="animate-spin text-primary" />
                                ) : (
                                  <Brain size={15} />
                                )}
                              </button>
                              <button
                                onClick={() => handleExtractEntities(fir.id)}
                                disabled={extractingId !== null || extractingEntitiesId !== null || indexingId !== null}
                                className="text-muted-foreground hover:text-amber-400 p-1.5 rounded-lg hover:bg-amber-500/10 transition-all flex items-center justify-center disabled:opacity-50"
                                title="Extract Entities"
                              >
                                {extractingEntitiesId === fir.id ? (
                                  <Loader2 size={15} className="animate-spin text-amber-400" />
                                ) : (
                                  <Sparkles size={15} />
                                )}
                              </button>
                              <button
                                onClick={() => handleIndexFIR(fir.id)}
                                disabled={extractingId !== null || extractingEntitiesId !== null || indexingId !== null}
                                className={`p-1.5 rounded-lg transition-all flex items-center justify-center disabled:opacity-50 ${
                                  fir.embedding 
                                    ? "text-indigo-400 hover:text-indigo-300 hover:bg-indigo-500/10" 
                                    : "text-muted-foreground hover:text-indigo-400 hover:bg-indigo-500/10"
                                }`}
                                title="Index FIR (Generate Embeddings)"
                              >
                                {indexingId === fir.id ? (
                                  <Loader2 size={15} className="animate-spin text-indigo-400" />
                                ) : (
                                  <Database size={15} />
                                )}
                              </button>
                              <button
                                onClick={() => handleFindSimilar(fir.id)}
                                disabled={extractingId !== null || extractingEntitiesId !== null || indexingId !== null || searchingSimilarId !== null}
                                className={`p-1.5 rounded-lg transition-all flex items-center justify-center disabled:opacity-50 ${
                                  fir.embedding 
                                    ? "text-sky-400 hover:text-sky-300 hover:bg-sky-500/10" 
                                    : "text-muted-foreground/40 hover:text-sky-400 hover:bg-sky-500/10 cursor-not-allowed"
                                }`}
                                title={fir.embedding ? "Find Similar Cases" : "Index this document first to find similar cases"}
                              >
                                {searchingSimilarId === fir.id ? (
                                  <Loader2 size={15} className="animate-spin text-sky-400" />
                                ) : (
                                  <FileSearch size={15} />
                                )}
                              </button>
                              <button
                                onClick={() => handleOpenCopilot(fir)}
                                className="text-muted-foreground hover:text-emerald-400 p-1.5 rounded-lg hover:bg-emerald-500/10 transition-all"
                                title="Chat with AI Copilot"
                              >
                                <MessageSquare size={15} />
                              </button>
                              <button
                                onClick={() => handleFetchRecommendations(fir)}
                                className="text-muted-foreground hover:text-amber-400 p-1.5 rounded-lg hover:bg-amber-500/10 transition-all flex items-center justify-center"
                                title="AI Investigation Recommendations"
                              >
                                <Lightbulb size={15} />
                              </button>
                              <button
                                onClick={() => handleDelete(fir.id)}
                                disabled={extractingId !== null || extractingEntitiesId !== null || indexingId !== null}
                                className="text-muted-foreground hover:text-red-400 p-1.5 rounded-lg hover:bg-red-500/10 transition-all disabled:opacity-50"
                                title="Delete FIR"
                              >
                                <Trash2 size={15} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>

      <Footer />

      {/* Extraction Result Modal */}
      {isExtractionModalOpen && selectedExtraction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-in fade-in duration-200">
          <div className="card-glass w-full max-w-2xl rounded-2xl border border-white/[0.08] shadow-2xl overflow-hidden flex flex-col max-h-[85vh] animate-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06] bg-white/[0.01]">
              <div>
                <h3 className="text-lg font-bold flex items-center gap-2">
                  <CheckCircle2 className="text-emerald-400" size={20} />
                  Document Text Extraction
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  FIR Case: {firs.find(f => f.id === selectedExtraction.fir_id)?.case_number || "Unknown"}
                </p>
              </div>
              <button
                onClick={() => {
                  setIsExtractionModalOpen(false);
                  setSelectedExtraction(null);
                }}
                className="text-muted-foreground hover:text-foreground transition-colors p-1 rounded-lg hover:bg-white/[0.04]"
              >
                <XCircle size={20} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-6 overflow-y-auto flex-1">
              {/* Stats Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="rounded-xl border border-white/[0.06] bg-white/[0.01] p-3 text-center">
                  <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Status</p>
                  <p className="text-sm font-bold text-emerald-400 mt-1 flex items-center justify-center gap-1">
                    <CheckCircle2 size={14} />
                    {selectedExtraction.extraction_status}
                  </p>
                </div>
                <div className="rounded-xl border border-white/[0.06] bg-white/[0.01] p-3 text-center">
                  <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Page Count</p>
                  <p className="text-base font-extrabold mt-1 text-foreground">{selectedExtraction.page_count}</p>
                </div>
                <div className="rounded-xl border border-white/[0.06] bg-white/[0.01] p-3 text-center">
                  <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Word Count</p>
                  <p className="text-base font-extrabold mt-1 text-foreground">{selectedExtraction.word_count}</p>
                </div>
                <div className="rounded-xl border border-white/[0.06] bg-white/[0.01] p-3 text-center">
                  <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Language</p>
                  <p className="text-base font-extrabold mt-1 text-foreground uppercase">{selectedExtraction.language || "en"}</p>
                </div>
              </div>

              {/* Character Count details */}
              <div className="flex items-center justify-between text-xs text-muted-foreground bg-white/[0.02] border border-white/[0.04] px-4 py-2 rounded-lg">
                <span>Character Count: <strong className="text-foreground">{selectedExtraction.character_count}</strong></span>
                <span>Extracted At: <strong className="text-foreground">{new Date(selectedExtraction.extracted_at).toLocaleString()}</strong></span>
              </div>

              {/* Preview block */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Text Preview (first 1000 characters)</h4>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(selectedExtraction.extracted_text);
                      showToast("success", "Copied", "Full text copied to clipboard.");
                    }}
                    className="text-xs text-primary hover:underline font-medium flex items-center gap-1"
                  >
                    <Copy size={12} />
                    Copy full text
                  </button>
                </div>
                <div className="rounded-xl border border-white/[0.08] bg-black/40 p-4 font-mono text-xs text-zinc-300 leading-relaxed overflow-y-auto max-h-48 whitespace-pre-wrap select-text">
                  {selectedExtraction.extracted_text.slice(0, 1000) || "No text could be previewed (empty file)."}
                  {selectedExtraction.extracted_text.length > 1000 && (
                    <span className="text-muted-foreground block mt-2 pt-2 border-t border-white/[0.04] italic">
                      ... [Truncated. Total characters: {selectedExtraction.character_count}]
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-white/[0.06] bg-white/[0.01]">
              <Button
                onClick={() => {
                  setIsExtractionModalOpen(false);
                  setSelectedExtraction(null);
                }}
                className="bg-white/10 hover:bg-white/20 text-white font-medium text-xs px-4 py-2 rounded-lg transition-colors border border-white/10"
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Entities Extraction Result Modal */}
      {isEntitiesModalOpen && selectedEntities && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-in fade-in duration-200">
          <div className="card-glass w-full max-w-3xl rounded-2xl border border-white/[0.08] shadow-2xl overflow-hidden flex flex-col max-h-[85vh] animate-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06] bg-white/[0.01]">
              <div>
                <h3 className="text-lg font-bold flex items-center gap-2 text-amber-400">
                  <Sparkles className="text-amber-400" size={20} />
                  AI Entity Extraction Results
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  FIR Case: {firs.find(f => f.id === activeEntityFirId)?.case_number || "Unknown"}
                </p>
              </div>
              <button
                onClick={() => {
                  setIsEntitiesModalOpen(false);
                  setSelectedEntities(null);
                }}
                className="text-muted-foreground hover:text-foreground transition-colors p-1 rounded-lg hover:bg-white/[0.04]"
              >
                <XCircle size={20} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-4 overflow-y-auto flex-1">
              {selectedEntities.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center space-y-3">
                  <AlertCircle size={40} className="text-zinc-500 animate-pulse" />
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-zinc-300">No entities extracted</p>
                    <p className="text-xs text-zinc-500 max-w-xs">Gemini did not find any recognizable entities in this document. Make sure the document contains plain text first.</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Summary / Total counter */}
                  <div className="flex items-center justify-between text-xs text-muted-foreground bg-white/[0.02] border border-white/[0.04] px-4 py-2.5 rounded-lg">
                    <span>Total Entities Found: <strong className="text-foreground">{selectedEntities.length}</strong></span>
                    <button
                      onClick={() => {
                        const textToCopy = selectedEntities.map(e => `[${e.entity_type.toUpperCase()}] ${e.entity_value} (Confidence: ${Math.round(e.confidence * 100)}%)`).join("\n");
                        navigator.clipboard.writeText(textToCopy);
                        showToast("success", "Copied", "All extracted entities copied to clipboard.");
                      }}
                      className="text-primary hover:underline font-semibold flex items-center gap-1"
                    >
                      <Copy size={12} />
                      Copy all entities
                    </button>
                  </div>

                  {/* Grouped entities layout */}
                  {Object.entries(
                    selectedEntities.reduce((acc: Record<string, any[]>, curr: any) => {
                      const type = curr.entity_type;
                      if (!acc[type]) acc[type] = [];
                      acc[type].push(curr);
                      return acc;
                    }, {})
                  ).map(([type, items]) => {
                    const isExpanded = expandedCategories[type] !== false;
                    const categoryLabels: Record<string, string> = {
                      person: "Persons of Interest",
                      victim: "Victims",
                      suspect: "Suspects",
                      witness: "Witnesses",
                      phone: "Phone Numbers",
                      email: "Email Addresses",
                      vehicle: "Vehicles Involved",
                      location: "Key Locations",
                      address: "Addresses",
                      date: "Dates Mentioned",
                      time: "Times Mentioned",
                      organization: "Organizations",
                      crime_category: "Crime Category",
                      weapon: "Weapons",
                      money: "Money/Financial Details",
                      evidence: "Evidence Items"
                    };
                    const friendlyLabel = categoryLabels[type] || type.toUpperCase();
                    
                    return (
                      <div key={type} className="rounded-xl border border-white/[0.06] bg-white/[0.01] overflow-hidden transition-all duration-300">
                        {/* Group Header */}
                        <div 
                          onClick={() => setExpandedCategories(prev => ({ ...prev, [type]: !isExpanded }))}
                          className="flex items-center justify-between px-4 py-3 bg-white/[0.02] border-b border-white/[0.04] cursor-pointer hover:bg-white/[0.04] select-none"
                        >
                          <div className="flex items-center gap-2">
                            <span className="p-1 rounded bg-amber-500/10 text-amber-400">
                              <Tags size={12} />
                            </span>
                            <span className="text-xs font-bold text-zinc-200">{friendlyLabel}</span>
                            <span className="inline-flex items-center rounded-full bg-zinc-800 px-1.5 py-0.5 text-[10px] font-semibold text-zinc-400">
                              {items.length}
                            </span>
                          </div>
                          <div className="flex items-center gap-3">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                const textToCopy = items.map(i => i.entity_value).join(", ");
                                navigator.clipboard.writeText(textToCopy);
                                showToast("success", "Copied", `Copied all ${friendlyLabel} to clipboard.`);
                              }}
                              className="text-[10px] text-primary hover:underline font-semibold flex items-center gap-1 opacity-70 hover:opacity-100 transition-opacity"
                            >
                              <Copy size={10} />
                              Copy category
                            </button>
                            {isExpanded ? <ChevronUp size={16} className="text-muted-foreground" /> : <ChevronDown size={16} className="text-muted-foreground" />}
                          </div>
                        </div>

                        {/* Collapsible Card Body */}
                        {isExpanded && (
                          <div className="p-3 bg-black/20 grid grid-cols-1 sm:grid-cols-2 gap-2 animate-in fade-in duration-200">
                            {items.map((item) => {
                              const confPercent = Math.round(item.confidence * 100);
                              const confColor = item.confidence >= 0.8 
                                ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" 
                                : item.confidence >= 0.5 
                                ? "text-amber-400 bg-amber-500/10 border-amber-500/20" 
                                : "text-red-400 bg-red-500/10 border-red-500/20";
                                
                              return (
                                <div key={item.id} className="flex items-center justify-between p-2.5 rounded-lg border border-white/[0.04] bg-white/[0.01] hover:border-white/[0.08] transition-all group">
                                  <div className="flex-1 min-w-0 pr-2">
                                    <div className="flex items-center gap-2 min-w-0">
                                      <p className="text-xs font-semibold text-zinc-100 truncate select-text" title={item.entity_value}>
                                        {item.entity_value}
                                      </p>
                                    </div>
                                    {/* Additional metadata tags if present */}
                                    {item.metadata && Object.keys(item.metadata).length > 0 && (
                                      <div className="flex flex-wrap gap-1 mt-1">
                                        {Object.entries(item.metadata).map(([k, v]) => (
                                          <span key={k} className="inline-flex items-center rounded px-1 py-0.25 text-[9px] font-medium bg-zinc-800 text-zinc-400 border border-white/[0.02]">
                                            {k}: {String(v)}
                                          </span>
                                        ))}
                                      </div>
                                    )}
                                  </div>

                                  <div className="flex items-center gap-2 shrink-0">
                                    {/* Confidence Pill */}
                                    <span className={`inline-flex items-center rounded-full px-1.5 py-0.5 text-[9px] font-semibold border ${confColor}`}>
                                      {confPercent}%
                                    </span>
                                    {/* Copy icon button */}
                                    <button
                                      onClick={() => {
                                        navigator.clipboard.writeText(item.entity_value);
                                        showToast("success", "Copied", `Copied value: "${item.entity_value}"`);
                                      }}
                                      className="text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-white/5 transition-all"
                                      title="Copy Entity"
                                    >
                                      <Copy size={11} />
                                    </button>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Explainability Panel */}
            <div className="px-6 pb-2">
              <ExplainabilityPanel data={entitiesExplainability} />
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-white/[0.06] bg-white/[0.01]">
              <Button
                onClick={() => {
                  setIsEntitiesModalOpen(false);
                  setSelectedEntities(null);
                }}
                className="bg-white/10 hover:bg-white/20 text-white font-medium text-xs px-4 py-2 rounded-lg transition-colors border border-white/10"
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Similar Cases Modal */}
      {isSimilarModalOpen && similarCases && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-in fade-in duration-200">
          <div className="card-glass w-full max-w-3xl rounded-2xl border border-white/[0.08] shadow-2xl overflow-hidden flex flex-col max-h-[85vh] animate-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06] bg-white/[0.01]">
              <div>
                <h3 className="text-base font-bold text-zinc-100 flex items-center gap-2">
                  <span className="p-1 rounded bg-sky-500/10 text-sky-400">
                    <FileSearch size={16} />
                  </span>
                  Similar Case Matches
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Query Case: <span className="font-semibold text-zinc-300">{similarCases.query_fir}</span>
                </p>
              </div>
              <button
                onClick={() => {
                  setIsSimilarModalOpen(false);
                  setSimilarCases(null);
                }}
                className="text-muted-foreground hover:text-zinc-200 transition-colors p-1"
              >
                <XCircle size={18} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
              {similarCases.matches.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <span className="p-3 rounded-full bg-zinc-800/40 text-muted-foreground/60 mb-3 border border-white/[0.04]">
                    <AlertCircle size={28} />
                  </span>
                  <h4 className="text-sm font-bold text-zinc-300">No Similar Cases Found</h4>
                  <p className="text-xs text-muted-foreground/80 mt-1 max-w-xs">
                    We couldn't find any historical FIRs matching the semantic profile of this document.
                  </p>
                </div>
              ) : (
                <div className="relative border-l border-white/[0.06] pl-6 ml-3 space-y-8">
                  {similarCases.matches.map((match: any, index: number) => {
                    const similarityColor = match.similarity >= 85
                      ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                      : match.similarity >= 60
                      ? "text-amber-400 bg-amber-500/10 border-amber-500/20"
                      : "text-slate-400 bg-slate-500/10 border-slate-500/20";
                    
                    return (
                      <div key={match.fir_id} className="relative group">
                        {/* Timeline node */}
                        <div className="absolute -left-[31px] top-1.5 w-3 h-3 rounded-full bg-zinc-900 border-2 border-sky-500 group-hover:scale-125 transition-transform" />

                        {/* Card */}
                        <div className="card-glass p-5 rounded-xl border border-white/[0.06] hover:border-white/[0.12] transition-all bg-white/[0.01]">
                          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold text-sky-400 uppercase tracking-wider">
                                #{index + 1}
                              </span>
                              <h4 className="text-sm font-bold text-zinc-100">
                                {match.case_number}
                              </h4>
                              <span className="inline-flex items-center rounded bg-white/[0.04] px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground border border-white/[0.06] capitalize">
                                {match.crime_type}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-bold border ${similarityColor}`}>
                                {match.similarity}% Match
                              </span>
                            </div>
                          </div>

                          {/* Reasons List */}
                          <div className="space-y-1.5 mb-4">
                            <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 mb-2">
                              Similarity Reasons
                            </p>
                            {match.reasons.map((reason: string, rIdx: number) => (
                              <div key={rIdx} className="flex items-start gap-2 text-xs text-zinc-300">
                                <span className="text-emerald-400 mt-0.5 bg-emerald-500/10 p-0.5 rounded-full shrink-0">
                                  <Check size={8} />
                                </span>
                                <span>{reason}</span>
                              </div>
                            ))}
                          </div>

                          {/* View details action */}
                          <div className="flex items-center justify-between border-t border-white/[0.04] pt-3.5 mt-3">
                            <div className="text-[10px] text-muted-foreground uppercase">
                              Status: <span className="font-bold text-zinc-400 capitalize">{match.status.replace("_", " ")}</span>
                            </div>
                            <Button
                              onClick={async () => {
                                try {
                                  setIsSimilarModalOpen(false);
                                  const resExt = await fetch(`${API_BASE_URL}/api/v1/firs/${match.fir_id}/extract`, { method: "POST" });
                                  if (resExt.ok) {
                                    const extData = await resExt.json();
                                    setSelectedExtraction(extData);
                                    setIsExtractionModalOpen(true);
                                  } else {
                                    showToast("error", "Error", "Failed to retrieve case details.");
                                  }
                                } catch (e) {
                                  showToast("error", "Error", "Could not load case details.");
                                }
                              }}
                              className="bg-white/5 hover:bg-white/10 text-zinc-300 border border-white/[0.06] text-xs font-semibold px-3 py-1 rounded-lg transition-colors flex items-center gap-1.5 h-7"
                            >
                              <FileText size={12} />
                              View Details
                            </Button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Explainability Panel */}
            <div className="px-6 pb-2">
              <ExplainabilityPanel data={similarExplainability} />
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-white/[0.06] bg-white/[0.01]">
              <Button
                onClick={() => {
                  setIsSimilarModalOpen(false);
                  setSimilarCases(null);
                }}
                className="bg-white/10 hover:bg-white/20 text-white font-medium text-xs px-4 py-2 rounded-lg transition-colors border border-white/10"
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Investigation Copilot Sidebar Drawer */}
      {isCopilotOpen && copilotFir && (
        <>
          {/* Backdrop */}
          <div
            onClick={() => setIsCopilotOpen(false)}
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-all duration-300 animate-in fade-in"
          />

          {/* Drawer Panel */}
          <div className="fixed top-0 right-0 z-50 h-full w-full sm:w-[460px] bg-zinc-950/95 border-l border-white/[0.08] shadow-2xl backdrop-blur-xl flex flex-col animate-in slide-in-from-right duration-300">
            {/* Header */}
            <div className="px-5 py-4 border-b border-white/[0.06] bg-white/[0.01] flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
                  <Bot size={18} />
                </span>
                <div>
                  <h3 className="text-sm font-bold text-zinc-100">AI Investigation Copilot</h3>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    Analyzing case <span className="font-semibold text-zinc-300">{copilotFir.case_number}</span>
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsCopilotOpen(false)}
                className="text-muted-foreground hover:text-zinc-200 transition-colors p-1.5 rounded-lg hover:bg-white/5"
              >
                <XCircle size={18} />
              </button>
            </div>

            {/* Suggested Question Chips */}
            <div className="px-5 py-3 border-b border-white/[0.04] bg-white/[0.01]">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/60 mb-2">
                Suggested Questions
              </p>
              <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
                {[
                  { label: "Summarize FIR", text: "Summarize this FIR." },
                  { label: "Who are the suspects?", text: "Who are the main suspects?" },
                  { label: "Show similar cases", text: "Show similar cases." },
                  { label: "List evidence", text: "What evidence is available?" },
                  { label: "Show locations", text: "Which locations appear repeatedly?" }
                ].map((sug) => (
                  <button
                    key={sug.label}
                    onClick={() => handleSendCopilotMessage(sug.text)}
                    disabled={isCopilotTyping}
                    className="text-[11px] text-zinc-300 bg-white/5 border border-white/[0.06] hover:bg-white/10 hover:border-white/[0.12] rounded-full px-2.5 py-1 transition-all disabled:opacity-50"
                  >
                    {sug.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Chat Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {chatHistory.map((chat, idx) => (
                <div
                  key={idx}
                  className={`flex ${chat.sender === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl p-4 text-xs leading-relaxed border ${
                      chat.sender === "user"
                        ? "bg-primary text-primary-foreground border-primary/20 rounded-tr-none"
                        : chat.isError
                        ? "bg-red-500/10 border-red-500/25 text-red-300 rounded-tl-none"
                        : "bg-white/[0.02] border-white/[0.06] text-zinc-200 rounded-tl-none"
                    }`}
                  >
                    <p className="whitespace-pre-wrap select-text">{chat.text}</p>

                    {/* Copilot Metadata & Sources */}
                    {chat.sender === "copilot" && !chat.isError && (
                      <div className="mt-3.5 pt-3 border-t border-white/[0.04] space-y-2">
                        {/* Confidence Indicator */}
                        {chat.confidence !== undefined && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] text-muted-foreground">Confidence:</span>
                            <span
                              className={`inline-flex items-center rounded-full px-1.5 py-0.25 text-[9px] font-bold border ${
                                chat.confidence >= 80
                                  ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                                  : chat.confidence >= 50
                                  ? "text-amber-400 bg-amber-500/10 border-amber-500/20"
                                  : "text-red-400 bg-red-500/10 border-red-500/20"
                              }`}
                            >
                              {chat.confidence}%
                            </span>
                          </div>
                        )}

                        {/* Sources cited */}
                        {chat.sources && chat.sources.length > 0 && (
                          <div className="flex flex-wrap items-center gap-1.5">
                            <span className="text-[10px] text-muted-foreground">Sources:</span>
                            {chat.sources.map((src: string) => (
                              <span
                                key={src}
                                className="inline-flex items-center rounded bg-white/[0.04] px-1 py-0.25 text-[9px] text-zinc-400 border border-white/[0.06] font-mono capitalize"
                              >
                                {src.replace("_", " ")}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Mastra Workflow Steps Collapsible */}
                        {chat.workflowSteps && chat.workflowSteps.length > 0 && (
                          <div className="text-[10px]">
                            <details className="outline-none group">
                              <summary className="text-muted-foreground/80 hover:text-zinc-300 cursor-pointer select-none font-semibold flex items-center gap-1">
                                <Cpu size={9} />
                                View Mastra Workflow Steps
                              </summary>
                              <div className="pl-3 mt-1.5 border-l border-emerald-500/30 py-1 space-y-1 animate-in fade-in duration-200">
                                {chat.workflowSteps.map((step: string, sIdx: number) => (
                                  <div key={step} className="flex items-center gap-1.5 text-zinc-400 font-mono text-[9px]">
                                    <span className="text-emerald-400">Step {sIdx + 1}:</span>
                                    <span>{step}</span>
                                  </div>
                                ))}
                              </div>
                            </details>
                          </div>
                        )}

                        {/* Explainability: Reasoning */}
                        {chat.reasoning && (
                          <div className="text-[10px]">
                            <details className="outline-none group">
                              <summary className="text-muted-foreground/80 hover:text-zinc-300 cursor-pointer select-none font-semibold flex items-center gap-1">
                                <Eye size={9} />
                                View Reasoning & Evidence
                              </summary>
                              <div className="pl-3 mt-1.5 border-l border-indigo-500/30 py-1 space-y-2 animate-in fade-in duration-200">
                                <p className="text-zinc-400 text-[10px] leading-relaxed">{chat.reasoning}</p>
                                {chat.supporting_entities && chat.supporting_entities.length > 0 && (
                                  <div className="flex flex-wrap gap-1">
                                    {chat.supporting_entities.map((ent: string, ei: number) => (
                                      <span key={ei} className="inline-flex items-center rounded bg-indigo-500/8 px-1 py-0.25 text-[8px] text-indigo-300 border border-indigo-500/15 font-mono">
                                        {ent}
                                      </span>
                                    ))}
                                  </div>
                                )}
                                {chat.limitations && chat.limitations.length > 0 && (
                                  <div className="space-y-0.5">
                                    {chat.limitations.map((lim: string, li: number) => (
                                      <div key={li} className="flex items-start gap-1 text-[9px] text-amber-300/70">
                                        <AlertCircle size={8} className="mt-0.5 shrink-0" />
                                        <span>{lim}</span>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </details>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {/* Typing state */}
              {isCopilotTyping && (
                <div className="flex justify-start">
                  <div className="bg-white/[0.02] border border-white/[0.06] rounded-2xl rounded-tl-none p-4 max-w-[85%] flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-bounce" />
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-bounce delay-100" />
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-bounce delay-200" />
                    <span className="text-[11px] text-muted-foreground ml-1">Copilot is running Mastra workflow...</span>
                  </div>
                </div>
              )}
            </div>

            {/* Input Footer */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendCopilotMessage(inputMessage);
              }}
              className="p-4 border-t border-white/[0.06] bg-black/20 flex gap-2"
            >
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Ask about victims, suspects, timeline, similar cases..."
                disabled={isCopilotTyping}
                className="flex-1 bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-2 text-xs text-zinc-100 placeholder-muted-foreground/60 focus:outline-none focus:border-emerald-500/50 transition-all disabled:opacity-50"
              />
              <Button
                type="submit"
                disabled={!inputMessage.trim() || isCopilotTyping}
                className="bg-emerald-500 hover:bg-emerald-600 text-zinc-950 font-bold p-2.5 rounded-xl transition-colors h-[34px] w-[34px] flex items-center justify-center shrink-0 disabled:opacity-50"
              >
                <Send size={14} />
              </Button>
            </form>
          </div>
        </>
      )}

      {/* AI Investigation Recommendations Drawer */}
      {isRecommendationsOpen && recommendationsFir && (
        <>
          {/* Backdrop */}
          <div
            onClick={() => setIsRecommendationsOpen(false)}
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-all duration-300 animate-in fade-in"
          />

          {/* Drawer Panel */}
          <div className="fixed top-0 right-0 z-50 h-full w-full sm:w-[460px] bg-zinc-950/95 border-l border-white/[0.08] shadow-2xl backdrop-blur-xl flex flex-col animate-in slide-in-from-right duration-300">
            {/* Header */}
            <div className="px-5 py-4 border-b border-white/[0.06] bg-white/[0.01] flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
                  <Lightbulb size={18} />
                </span>
                <div>
                  <h3 className="text-sm font-bold text-zinc-100">AI Investigation Leads</h3>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    Recommended steps for <span className="font-semibold text-zinc-300">{recommendationsFir.case_number}</span>
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsRecommendationsOpen(false)}
                className="text-muted-foreground hover:text-zinc-200 transition-colors p-1.5 rounded-lg hover:bg-white/5"
              >
                <XCircle size={18} />
              </button>
            </div>

            {/* Category Filter Pills */}
            <div className="px-5 py-3 border-b border-white/[0.04] bg-white/[0.01] overflow-x-auto flex gap-1.5 scrollbar-thin">
              {["All", "Evidence Collection", "Witness Actions", "Location Investigation", "Suspect Investigation"].map((cat) => (
                <button
                  key={cat}
                  onClick={() => setRecommendationsFilter(cat)}
                  className={`px-3 py-1 rounded-full text-[10px] font-bold whitespace-nowrap transition-all border ${
                    recommendationsFilter === cat
                      ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                      : "bg-white/[0.02] text-zinc-400 border-white/[0.05] hover:bg-white/5"
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>

            {/* Explainability Panel */}
            {recommendationsExplainability && !loadingRecommendations && (
              <div className="px-5 py-2 border-b border-white/[0.04]">
                <ExplainabilityPanel data={recommendationsExplainability} />
              </div>
            )}

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {loadingRecommendations ? (
                <div className="h-48 flex flex-col items-center justify-center text-center space-y-3">
                  <Loader2 size={24} className="animate-spin text-amber-400" />
                  <p className="text-xs text-muted-foreground">Running Gemini investigation models...</p>
                </div>
              ) : recommendationsError ? (
                <div className="card-glass border border-white/[0.08] bg-zinc-900/40 rounded-2xl p-5 text-center space-y-3">
                  <div className="p-2.5 rounded-full bg-amber-500/5 text-amber-400 w-fit mx-auto border border-amber-500/10">
                    <AlertCircle size={20} />
                  </div>
                  <p className="text-xs font-semibold text-zinc-200">Recommendations Status</p>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {recommendationsError}
                  </p>
                </div>
              ) : recommendations && recommendations.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-xs text-muted-foreground">No actionable recommendations found.</p>
                </div>
              ) : (
                <div className="space-y-3.5">
                  {(recommendations || [])
                    .filter((rec) => recommendationsFilter === "All" || rec.category === recommendationsFilter)
                    .map((rec, idx) => {
                      const isCompleted = completedRecommendations.includes(rec.title);
                      return (
                        <div
                          key={idx}
                          className={`card-glass border rounded-2xl p-4 transition-all duration-300 flex flex-col gap-3.5 ${
                            isCompleted
                              ? "border-emerald-500/20 bg-emerald-950/5 opacity-60"
                              : "border-white/[0.08] bg-white/[0.01] hover:border-white/[0.15]"
                          }`}
                        >
                          {/* Top Row: Category badge & Priority */}
                          <div className="flex items-center justify-between">
                            <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-white/[0.04] text-zinc-300 border border-white/[0.06]">
                              {rec.category}
                            </span>
                            <div className="flex items-center gap-2">
                              <span
                                className={`px-2 py-0.5 rounded text-[9px] font-bold border ${
                                  rec.priority === "High"
                                    ? "bg-red-500/10 text-red-400 border-red-500/20"
                                    : rec.priority === "Medium"
                                    ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                                    : "bg-zinc-500/10 text-zinc-400 border-zinc-500/20"
                                }`}
                              >
                                {rec.priority} Priority
                              </span>
                              <span className="text-[10px] text-muted-foreground font-medium">
                                {rec.confidence}% confidence
                              </span>
                            </div>
                          </div>

                          {/* Title & Description */}
                          <div className="space-y-1.5">
                            <h4
                              className={`text-xs font-bold leading-snug select-text ${
                                isCompleted ? "line-through text-zinc-500" : "text-zinc-100"
                              }`}
                            >
                              {rec.title}
                            </h4>
                            <p className="text-[11px] text-muted-foreground select-text leading-relaxed">
                              {rec.reason}
                            </p>
                          </div>

                          {/* Footer Action Bar */}
                          <div className="flex items-center justify-between border-t border-white/[0.04] pt-3.5 mt-0.5">
                            {/* Mark completed */}
                            <button
                              onClick={() => {
                                setCompletedRecommendations((prev) =>
                                  isCompleted
                                    ? prev.filter((t) => t !== rec.title)
                                    : [...prev, rec.title]
                                );
                              }}
                              className={`flex items-center gap-1.5 text-[10px] font-bold px-2.5 py-1.5 rounded-lg border transition-all ${
                                isCompleted
                                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20"
                                  : "bg-white/[0.02] text-zinc-400 border-white/[0.05] hover:bg-white/5"
                              }`}
                            >
                              <Check size={11} />
                              {isCompleted ? "Completed" : "Mark Done"}
                            </button>

                            {/* Copy recommendation */}
                            <button
                              onClick={() => {
                                navigator.clipboard.writeText(`[${rec.category}] ${rec.title}\nReason: ${rec.reason}`);
                                showToast("success", "Copied", "Lead details copied to clipboard");
                              }}
                              className="p-1.5 rounded-lg bg-white/[0.02] border border-white/[0.05] text-muted-foreground hover:text-zinc-200 hover:bg-white/5 transition-all flex items-center justify-center"
                              title="Copy details"
                            >
                              <Copy size={11} />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* Floating Animated Toasts Container */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 w-full max-w-sm">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`flex items-start gap-3 rounded-xl p-4 shadow-xl border backdrop-blur-xl transition-all duration-300 animate-in slide-in-from-right-5 ${
              toast.type === "success"
                ? "bg-emerald-950/80 border-emerald-500/30 text-emerald-200"
                : toast.type === "error"
                ? "bg-red-950/80 border-red-500/30 text-red-200"
                : "bg-zinc-900/90 border-zinc-800 text-zinc-200"
            }`}
          >
            {toast.type === "success" && <CheckCircle2 size={18} className="text-emerald-400 shrink-0 mt-0.5" />}
            {toast.type === "error" && <XCircle size={18} className="text-red-400 shrink-0 mt-0.5" />}
            {toast.type === "info" && <AlertCircle size={18} className="text-primary shrink-0 mt-0.5" />}

            <div className="flex-1 space-y-0.5">
              <p className="text-sm font-bold">{toast.title}</p>
              <p className="text-xs opacity-90 leading-relaxed">{toast.message}</p>
            </div>

            <button
              onClick={() => removeToast(toast.id)}
              className="opacity-60 hover:opacity-100 text-sm shrink-0 transition-opacity"
            >
              <XCircle size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
