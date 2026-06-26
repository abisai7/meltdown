import { useState, useRef, useEffect } from "react";
import Markdown from "react-markdown";

const ACCEPTED = ".pdf,.docx,.pptx,.xlsx,.html,.htm,.txt,.csv,.jpg,.jpeg,.png,.mp3,.wav,.zip,.epub";

export default function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [tab, setTab] = useState("markdown");
  const inputRef = useRef();
  const textareaRef = useRef();

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.value = result;
    }
  }, [result]);

  const handleFile = (f) => {
    setFile(f);
    setResult("");
    setError("");
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const handleConvert = async () => {
    if (!file) return;
    setLoading(true);
    setError("");
    setResult("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/convert", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Conversion failed.");
      }

      const text = await res.text();
      setResult(text);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([result], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const baseName = file?.name?.replace(/\.[^.]+$/, "") || "converted";
    a.href = url;
    a.download = `${baseName}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <main>
      <h1>Meltdown</h1>
      <p>Convert documents to Markdown — no files stored.</p>

      <div
        className={`dropzone ${dragging ? "dragging" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          style={{ display: "none" }}
          onChange={(e) => handleFile(e.target.files[0])}
        />
        {file ? (
          <p>📄 <strong>{file.name}</strong> ({(file.size / 1024).toFixed(1)} KB)</p>
        ) : (
          <p>Drag & drop a file here, or click to browse</p>
        )}
      </div>

      <button onClick={handleConvert} disabled={!file || loading}>
        {loading ? "Converting…" : "Convert to Markdown"}
      </button>

      {error && <p className="error">⚠ {error}</p>}

      {result && (
        <>
          <div className="result-header">
            <div className="tabs">
              <button className={tab === "markdown" ? "active" : ""} onClick={() => setTab("markdown")}>Markdown</button>
              <button className={tab === "preview" ? "active" : ""} onClick={() => setTab("preview")}>Preview</button>
            </div>
            <button onClick={handleDownload}>⬇ Download .md</button>
          </div>
          <textarea ref={textareaRef} defaultValue="" rows={20} onInput={(e) => setResult(e.target.value)} style={{ display: tab === "markdown" ? "block" : "none" }} />
          <div className="preview" style={{ display: tab === "preview" ? "block" : "none" }}>
            <Markdown>{result}</Markdown>
          </div>
        </>
      )}
    </main>
  );
}
