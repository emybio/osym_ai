const API_URL = import.meta.env.VITE_API_URL;

import React, { useState, useCallback, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useProtectedRoute } from '../hooks/useProtectedRoute';
import {
  Upload,
  File,
  CheckCircle,
  AlertCircle,
  Trash2,
  BookOpen
} from 'lucide-react';
import LoadingSpinner from './LoadingSpinner';

const PDFUploadPage = ({ onLogout }) => {
  const { user, logout, loading: authLoading } = useAuth();
  const { canAccess, isChecking, reason } = useProtectedRoute(true);

  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadResults, setUploadResults] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [fileMetadata, setFileMetadata] = useState({});
  const [subjects, setSubjects] = useState([]);
  const [loadingSubjects, setLoadingSubjects] = useState(true);

  // 🔥 Yeni: auth yüklenmeden hiçbir sayfa render edilmez
  if (authLoading || user === undefined || isChecking) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <LoadingSpinner size="large" text="Yetki kontrol ediliyor..." />
      </div>
    );
  }

  // 🔒 Kullanıcı admin değilse gerçek erişim reddi
  if (!canAccess) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="max-w-md w-full bg-white rounded-xl shadow-lg border border-gray-200 p-8 text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Erişim Reddedildi</h2>
          <p className="text-gray-600 mb-6">
            {reason || "Bu sayfaya erişim yetkiniz bulunmamaktadır."}
          </p>
          <button
            onClick={() => logout(onLogout)}
            className="w-full px-4 py-2 mt-4 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Çıkış Yap
          </button>
        </div>
      </div>
    );
  }

  // -----------------------------------------------
  // 🟦 Subject Fetch
  // -----------------------------------------------
  useEffect(() => {
    const fetchSubjects = async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/subjects/`);
        const data = await res.json();
        setSubjects(data);
      } catch (error) {
        console.error("Failed to fetch subjects:", error);
      } finally {
        setLoadingSubjects(false);
      }
    };

    fetchSubjects();
  }, []);

  // -----------------------------------------------
  // 🟦 Drag & Drop
  // -----------------------------------------------
  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  }, []);

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files);
    }
  };

  // -----------------------------------------------
  // 🟦 File Processing
  // -----------------------------------------------
  const handleFiles = (newFiles) => {
    const valid = Array.from(newFiles).filter(f =>
      f.type === 'application/pdf' && f.size <= 50 * 1024 * 1024
    );

    if (valid.length === 0) {
      alert("Geçerli PDF seçin (maks 50MB)");
      return;
    }

    const combined = [...files, ...valid];
    setFiles(combined);

    const newMetadata = { ...fileMetadata };
    valid.forEach(file => {
      newMetadata[file.name] = newMetadata[file.name] || {
        title: file.name.replace('.pdf', ''),
        description: '',
        document_type: 'PAST_EXAM',
        subject_code: '',
        exam_type: 'TYT',
        year: new Date().getFullYear().toString()
      };
    });
    setFileMetadata(newMetadata);
  };

  const updateFileMetadata = (name, field, value) => {
    setFileMetadata(prev => ({
      ...prev,
      [name]: { ...prev[name], [field]: value }
    }));
  };

  const removeFile = (name) => {
    setFiles(files.filter(f => f.name !== name));
    const meta = { ...fileMetadata };
    delete meta[name];
    setFileMetadata(meta);
  };

  // -----------------------------------------------
  // 🟦 Upload Handler
  // -----------------------------------------------
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (files.length === 0) {
      alert('PDF seçmediniz');
      return;
    }

    setUploading(true);
    setUploadResults(null);

    try {
      const formData = new FormData();

      files.forEach(file => formData.append('files', file));

      files.forEach(file => {
        const meta = fileMetadata[file.name];
        Object.entries(meta).forEach(([key, val]) => {
          formData.append(`${key}_${file.name}`, val);
        });
      });

      const res = await fetch(`${API_URL}/quiz/pdf/upload/`, {
        method: "POST",
        credentials: "include",
        body: formData
      });

      const data = await res.json();

      setUploadResults({ success: true, ...data });
      setFiles([]);
      setFileMetadata({});

    } catch (err) {
      setUploadResults({
        success: false,
        error: err.message
      });
    } finally {
      setUploading(false);
    }
  };

  // -----------------------------------------------
  // 🟦 UI
  // -----------------------------------------------
  return (
    <div className="min-h-screen bg-gray-50">

      {/* HEADER */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Upload className="w-8 h-8 text-blue-600" />
            <div>
              <h1 className="text-2xl font-bold">PDF Yükleme Paneli</h1>
              <p className="text-gray-600">Yönetici: {user?.username}</p>
            </div>
          </div>
          <button
            onClick={() => logout(onLogout)}
            className="px-4 py-2 text-sm bg-white border rounded-lg hover:bg-gray-50"
          >
            Çıkış Yap
          </button>
        </div>
      </div>

      {/* MAIN */}
      <div className="max-w-4xl mx-auto p-6">

        <div className="bg-white rounded-xl shadow p-6 border">

          <div className="flex items-center gap-2 mb-6">
            <BookOpen className="w-6 h-6 text-blue-600" />
            <h2 className="text-xl font-bold">Soru Bankası PDF Yükle</h2>
          </div>

          {/* Upload Area */}
          <div
            className={`relative border-2 border-dashed rounded-xl p-8 text-center ${
              dragActive ? "border-blue-500 bg-blue-50" : "border-gray-300"
            }`}
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
          >
            <input
              type="file"
              multiple
              accept=".pdf"
              onChange={handleFileSelect}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />

            <Upload className="w-10 h-10 mx-auto text-gray-400" />

            <p className="text-lg mt-3">
              PDF dosyalarını buraya sürükle veya tıkla
            </p>
          </div>

          {/* File list */}
          {files.length > 0 && (
            <div className="mt-8 space-y-4">
              {files.map((file, idx) => (
                <div key={idx} className="border rounded-lg p-4 bg-gray-50">

                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium">{file.name}</p>
                      <p className="text-sm text-gray-500">
                        {(file.size / (1024 * 1024)).toFixed(2)} MB
                      </p>
                    </div>

                    <button
                      onClick={() => removeFile(file.name)}
                      className="p-1 hover:bg-gray-200 rounded"
                    >
                      <Trash2 className="w-4 h-4 text-gray-500" />
                    </button>
                  </div>

                  {/* Metadata */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">

                    {/* Title */}
                    <div>
                      <label className="text-sm">Başlık</label>
                      <input
                        type="text"
                        className="w-full px-3 py-2 border rounded-lg"
                        value={fileMetadata[file.name]?.title || ""}
                        onChange={e =>
                          updateFileMetadata(file.name, "title", e.target.value)
                        }
                      />
                    </div>

                    {/* Subject */}
                    <div>
                      <label className="text-sm">Ders</label>
                      <select
                        className="w-full px-3 py-2 border rounded-lg"
                        value={fileMetadata[file.name]?.subject_code || ""}
                        onChange={e =>
                          updateFileMetadata(file.name, "subject_code", e.target.value)
                        }
                      >
                        <option value="">Seç</option>
                        {subjects.map(sub => (
                          <option key={sub.id} value={sub.code}>
                            {sub.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Document Type */}
                    <div>
                      <label className="text-sm">Doküman Türü</label>
                      <select
                        className="w-full px-3 py-2 border rounded-lg"
                        value={fileMetadata[file.name]?.document_type || ""}
                        onChange={e =>
                          updateFileMetadata(file.name, "document_type", e.target.value)
                        }
                      >
                        <option value="PAST_EXAM">Geçmiş Sınav</option>
                        <option value="CURRICULUM">Müfredat</option>
                      </select>
                    </div>

                    {/* Exam Type */}
                    <div>
                      <label className="text-sm">Sınav Türü</label>
                      <select
                        className="w-full px-3 py-2 border rounded-lg"
                        value={fileMetadata[file.name]?.exam_type || "TYT"}
                        onChange={e =>
                          updateFileMetadata(file.name, "exam_type", e.target.value)
                        }
                      >
                        <option value="TYT">TYT</option>
                        <option value="AYT">AYT</option>
                        <option value="BOTH">Her İkisi</option>
                      </select>
                    </div>

                    {/* Year */}
                    <div>
                      <label className="text-sm">Yıl</label>
                      <input
                        className="w-full px-3 py-2 border rounded-lg"
                        value={fileMetadata[file.name]?.year || ""}
                        onChange={e =>
                          updateFileMetadata(file.name, "year", e.target.value)
                        }
                      />
                    </div>

                    {/* Description */}
                    <div className="col-span-2">
                      <label className="text-sm">Açıklama</label>
                      <textarea
                        className="w-full px-3 py-2 border rounded-lg"
                        rows="2"
                        value={fileMetadata[file.name]?.description || ""}
                        onChange={e =>
                          updateFileMetadata(file.name, "description", e.target.value)
                        }
                      ></textarea>
                    </div>

                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Upload Button */}
          <div className="flex justify-center mt-6">
            <button
              onClick={handleSubmit}
              disabled={files.length === 0 || uploading}
              className={`px-8 py-3 rounded-lg font-medium flex items-center gap-3 ${
                files.length === 0 || uploading
                  ? "bg-gray-300 text-gray-600 cursor-not-allowed"
                  : "bg-blue-600 text-white hover:bg-blue-700"
              }`}
            >
              {uploading ? (
                <>
                  <LoadingSpinner size="small" />
                  Yükleniyor...
                </>
              ) : (
                <>
                  <Upload className="w-5 h-5" />
                  {files.length} Dosyayı Yükle
                </>
              )}
            </button>
          </div>

          {/* Upload Results */}
          {uploadResults && (
            <div
              className={`mt-6 p-4 rounded-lg ${
                uploadResults.success
                  ? "bg-green-50 border border-green-200"
                  : "bg-red-50 border border-red-200"
              }`}
            >
              <div className="flex items-center gap-3">
                {uploadResults.success ? (
                  <CheckCircle className="w-6 h-6 text-green-600" />
                ) : (
                  <AlertCircle className="w-6 h-6 text-red-600" />
                )}

                <div>
                  <h4 className="font-bold">
                    {uploadResults.success ? "Yükleme Başarılı" : "Yükleme Hatası"}
                  </h4>
                  <p className="text-sm mt-1">
                    {uploadResults.success
                      ? `${uploadResults.success_count} dosya yüklendi.`
                      : uploadResults.error}
                  </p>
                </div>
              </div>
            </div>
          )}

        </div>
      </div>

    </div>
  );
};

export default PDFUploadPage;
