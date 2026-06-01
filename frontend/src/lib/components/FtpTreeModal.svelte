<script lang="ts">
	type FtpConfig = {
		enabled: boolean;
		protocol: string;
		host: string;
		port: number;
		username: string;
		password: string;
		passive: boolean;
	};

	type TreeNode = {
		name: string;
		path: string;
		is_dir: boolean;
		depth: number;
		children: TreeNode[];
		expanded: boolean;
		loading: boolean;
	};

	let {
		isOpen = $bindable(false),
		ftpConfig,
		initialPath = "/",
		onConfirm,
	}: {
		isOpen: boolean;
		ftpConfig: FtpConfig;
		initialPath?: string;
		onConfirm: (path: string) => void;
	} = $props();

	let rootNodes = $state<TreeNode[]>([]);
	let selectedPath = $state<string>("/");
	let loadingRoot = $state(false);
	let error = $state("");

	async function fetchEntries(path: string, depth: number): Promise<TreeNode[]> {
		const res = await fetch("/ftp/browse", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ config: ftpConfig, path }),
		});
		if (!res.ok) {
			const data = await res.json();
			throw new Error(data.detail || "Browse failed");
		}
		const entries: { name: string; path: string; is_dir: boolean }[] = await res.json();
		return entries.map((e) => ({
			...e,
			depth,
			children: [],
			expanded: false,
			loading: false,
		}));
	}

	async function loadRoot() {
		loadingRoot = true;
		error = "";
		const startPath = initialPath && initialPath !== "/" ? initialPath : "/";
		try {
			rootNodes = await fetchEntries(startPath, 1);
		} catch (e: any) {
			// initialPath가 유효하지 않으면 루트로 폴백
			if (startPath !== "/") {
				try {
					rootNodes = await fetchEntries("/", 1);
				} catch (e2: any) {
					error = e2.message;
				}
			} else {
				error = e.message;
			}
		} finally {
			loadingRoot = false;
		}
	}

	// Flatten the tree for rendering
	function flattenTree(nodes: TreeNode[]): TreeNode[] {
		const result: TreeNode[] = [];
		for (const node of nodes) {
			result.push(node);
			if (node.is_dir && node.expanded) {
				result.push(...flattenTree(node.children));
			}
		}
		return result;
	}

	let flatNodes = $derived(flattenTree(rootNodes));

	async function toggleExpand(node: TreeNode) {
		if (!node.is_dir) return;
		if (node.expanded) {
			node.expanded = false;
			return;
		}
		if (node.children.length === 0) {
			node.loading = true;
			rootNodes = rootNodes; // trigger reactivity
			try {
				node.children = await fetchEntries(node.path, node.depth + 1);
			} catch (e: any) {
				error = e.message;
			} finally {
				node.loading = false;
			}
		}
		node.expanded = true;
		rootNodes = rootNodes;
	}

	// New folder state
	let showNewFolder = $state(false);
	let newFolderName = $state("");
	let creatingFolder = $state(false);
	let folderError = $state("");

	function startNewFolder() {
		showNewFolder = true;
		newFolderName = "";
		folderError = "";
	}

	async function createFolder() {
		const name = newFolderName.trim();
		if (!name) return;
		const newPath = selectedPath.replace(/\/$/, "") + "/" + name;
		creatingFolder = true;
		folderError = "";
		try {
			const res = await fetch("/ftp/mkdir", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ config: ftpConfig, path: newPath }),
			});
			if (!res.ok) {
				const data = await res.json();
				throw new Error(data.detail || "Failed to create folder");
			}
			showNewFolder = false;
			newFolderName = "";
			// Refresh children of the currently selected node
			const refreshNode = flatNodes.find((n) => n.path === selectedPath);
			if (refreshNode) {
				refreshNode.children = [];
				refreshNode.expanded = false;
				await toggleExpand(refreshNode);
			} else {
				// selected is the root entry — reload root
				rootNodes = await fetchEntries(initialPath || "/", 1);
			}
			selectedPath = newPath;
		} catch (e: any) {
			folderError = e.message;
		} finally {
			creatingFolder = false;
		}
	}

	function handleConfirm() {
		onConfirm(selectedPath);
		isOpen = false;
	}

	$effect(() => {
		if (isOpen) {
			document.body.style.overflow = "hidden";
			const start = initialPath || "/";
			selectedPath = start;
			rootNodes = [];
			error = "";
			loadRoot();
		} else {
			document.body.style.overflow = "";
		}
		return () => {
			document.body.style.overflow = "";
		};
	});
</script>

{#if isOpen}
	<div
		class="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
	>
		<div
			class="bg-slate-900 rounded-2xl shadow-2xl border border-slate-800 w-full max-w-2xl flex flex-col"
			style="max-height: 85vh; min-height: 400px;"
		>
			<!-- Header -->
			<div class="flex items-center justify-between px-6 py-4 border-b border-slate-800 shrink-0">
				<div>
					<h3 class="text-lg font-bold text-white">Select Upload Destination</h3>
					<p class="text-xs text-slate-500 mt-0.5">
						{ftpConfig.protocol.toUpperCase()} · {ftpConfig.host}:{ftpConfig.port}
					</p>
				</div>
				<button
					onclick={() => (isOpen = false)}
					class="text-slate-500 hover:text-white transition-colors p-1"
				>
					<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<!-- Selected path display -->
			<div class="px-4 py-2.5 bg-slate-950/60 border-b border-slate-800 flex items-center gap-2 shrink-0">
				<svg class="w-4 h-4 text-blue-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
				</svg>
				<span class="text-sm font-mono text-blue-300 truncate flex-1" title={selectedPath}>{selectedPath}</span>
				<button
					onclick={startNewFolder}
					title="Create new folder inside selected path"
					class="flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-emerald-400 transition-colors px-2 py-1 rounded-lg hover:bg-emerald-500/10 shrink-0"
				>
					<svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
					</svg>
					New Folder
				</button>
			</div>

			<!-- Inline new folder input -->
			{#if showNewFolder}
				<div class="px-4 py-2.5 bg-emerald-500/5 border-b border-emerald-500/20 flex items-center gap-2 shrink-0">
					<svg class="w-4 h-4 text-emerald-500 shrink-0" fill="currentColor" viewBox="0 0 20 20">
						<path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
					</svg>
					<span class="text-xs text-slate-500 font-mono truncate shrink-0">{selectedPath.replace(/\/$/, "")}/</span>
					<input
						type="text"
						bind:value={newFolderName}
						placeholder="folder_name"
						onkeydown={(e) => { if (e.key === "Enter") createFolder(); if (e.key === "Escape") showNewFolder = false; }}
						class="flex-1 min-w-0 bg-slate-800 border border-emerald-500/40 text-slate-200 font-mono text-sm rounded-lg px-3 py-1.5 focus:ring-1 focus:ring-emerald-500 outline-none"
					/>
					<button
						onclick={createFolder}
						disabled={creatingFolder || !newFolderName.trim()}
						class="shrink-0 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-bold px-3 py-1.5 rounded-lg transition-all flex items-center gap-1"
					>
						{#if creatingFolder}
							<div class="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin"></div>
						{:else}
							Create
						{/if}
					</button>
					<button
						onclick={() => (showNewFolder = false)}
						class="shrink-0 text-slate-500 hover:text-slate-300 transition-colors p-1"
					>
						<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
				{#if folderError}
					<div class="px-4 py-2 bg-red-500/10 border-b border-red-500/20 text-xs text-red-400">{folderError}</div>
				{/if}
			{/if}

			<!-- Tree content -->
			<div class="flex-1 overflow-y-auto overscroll-contain p-3 min-h-0 space-y-0.5">
				{#if loadingRoot}
					<div class="flex items-center justify-center py-16">
						<div class="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
					</div>
				{:else if error}
					<div class="text-red-400 text-sm p-4 bg-red-500/10 rounded-xl border border-red-500/20">
						{error}
					</div>
				{:else}
					<!-- Root entry (initialPath or "/") -->
					<button
						onclick={() => (selectedPath = initialPath || "/")}
						class="w-full text-left flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors {selectedPath === (initialPath || '/') ? 'bg-blue-600/20 text-blue-300 border border-blue-600/30' : 'hover:bg-white/5 text-slate-400'}"
					>
						<svg class="w-4 h-4 text-yellow-500 shrink-0" fill="currentColor" viewBox="0 0 20 20">
							<path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
						</svg>
						<span class="font-medium font-mono">{initialPath && initialPath !== "/" ? initialPath : "/ (root)"}</span>
					</button>

					{#each flatNodes as node}
						{#if node.is_dir}
							<button
								onclick={async () => {
									selectedPath = node.path;
									await toggleExpand(node);
								}}
								style="padding-left: {node.depth * 16 + 12}px"
								class="w-full text-left flex items-center gap-2 pr-3 py-1.5 rounded-lg text-sm transition-colors {selectedPath === node.path ? 'bg-blue-600/20 text-blue-300 border border-blue-600/30' : 'hover:bg-white/5 text-slate-300'}"
							>
								<!-- Expand/collapse arrow -->
								<div class="w-4 h-4 shrink-0 flex items-center justify-center">
									{#if node.loading}
										<div class="w-3 h-3 border border-blue-400 border-t-transparent rounded-full animate-spin"></div>
									{:else}
										<svg
											class="w-3 h-3 transition-transform {node.expanded ? 'rotate-90' : ''}"
											fill="none"
											viewBox="0 0 24 24"
											stroke="currentColor"
										>
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M9 5l7 7-7 7" />
										</svg>
									{/if}
								</div>
								<!-- Folder icon -->
								<svg
									class="w-4 h-4 shrink-0 {node.expanded ? 'text-yellow-400' : 'text-yellow-600'}"
									fill="currentColor"
									viewBox="0 0 20 20"
								>
									<path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
								</svg>
								<span class="truncate font-mono text-xs">{node.name}</span>
							</button>
						{/if}
					{/each}

					{#if flatNodes.filter((n) => n.is_dir).length === 0}
						<div class="text-center text-slate-600 py-8 text-sm italic">No folders found</div>
					{/if}
				{/if}
			</div>

			<!-- Footer -->
			<div class="px-6 py-4 border-t border-slate-800 flex items-center justify-between gap-4 shrink-0">
				<p class="text-xs text-slate-500">
					Files will be uploaded to: <span class="text-blue-400 font-mono">{selectedPath}</span>
				</p>
				<div class="flex gap-3">
					<button
						onclick={() => (isOpen = false)}
						class="px-5 py-2 rounded-xl text-sm font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition-all"
					>
						Cancel
					</button>
					<button
						onclick={handleConfirm}
						class="px-6 py-2 rounded-xl text-sm font-bold bg-blue-600 hover:bg-blue-500 text-white transition-all flex items-center gap-2"
					>
						<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
						</svg>
						Select Folder
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}
