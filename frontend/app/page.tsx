import Twin from "@/components/twin";

export default function Home() {
  return (
    <main className="h-screen bg-gradient-to-br from-slate-50 to-gray-100 flex flex-col overflow-hidden">
      <div className="container mx-auto px-4 pt-8 flex flex-col flex-1 min-h-0">
        <div className="max-w-4xl mx-auto w-full flex flex-col flex-1 min-h-0">
          {/* Profile Hero */}
          <div className="flex flex-col items-center mb-6 shrink-0">
            <img
              src="/hopeogbons.png"
              alt="Hope Ogbons"
              className="w-24 h-24 rounded-full object-cover object-top ring-4 ring-slate-200 shadow-lg mb-4"
            />
            <h1 className="text-4xl font-bold text-center text-gray-800 mb-2">
              Hope Ogbons
            </h1>
            <p className="text-center text-gray-600 max-w-2xl">
              Senior Agentic / Forward-Deployed AI Engineer
            </p>
          </div>

          {/* Chat */}
          <div className="flex-1 min-h-0">
            <Twin />
          </div>
        </div>
      </div>

      <footer className="shrink-0 py-4 text-center text-sm text-gray-500">
        <p>AI Digital Twin @hopeogbons</p>
      </footer>
    </main>
  );
}
