<script lang="ts">
	import { onMount } from "svelte";
	import { goto } from "$app/navigation";
	import logo from "$lib/assets/logo.png";
	import FtpTreeModal from "$lib/components/FtpTreeModal.svelte";

	let config = $state({
		default_task_name: "Compositing",
		filename_pattern: "{episode}_{sequence}_{shot}_{task}_v{version}",
		sequence_name_template: "{episode}_{sequence}",
		shot_name_template: "{episode}_{sequence}_{shot}",
	});

	// 글로벌 FTP 접속 설정
	let ftpConfig = $state({
		enabled: false,
		protocol: "sftp",
		host: "",
		port: 22,
		username: "",
		password: "",
		passive: true,
	});
	// 프로젝트별 FTP 루트 경로
	let ftpRemoteRoot = $state("/");

	let ftpTesting = $state(false);
	let ftpTestResult = $state<{ ok: boolean; message: string } | null>(null);
	let showFtpPassword = $state(false);
	let ftpTreeOpen = $state(false);

	let projects = $state<any[]>([]);
	let selectedProjectId = $state("global"); // 'global' or project_id

	let previewFilename = $state("EP01_SQ01_SH010_Comp_v001.mov");
	let previewResult = $state<any>(null);
	let message = $state("");

	onMount(async () => {
		await loadProjects();
		await loadConfig();
	});

	async function loadProjects() {
		try {
			const res = await fetch("/kitsu/projects");
			if (res.ok) {
				projects = await res.json();
			}
		} catch (e) {
			console.error("Failed to load projects", e);
		}
	}

	async function loadConfig() {
		// 파일명 파싱 설정 로드
		try {
			const url =
				selectedProjectId === "global"
					? "/system/config"
					: `/system/config/projects/${selectedProjectId}`;
			const res = await fetch(url);
			if (res.ok) {
				const data = await res.json();
				config = {
					default_task_name: data.default_task_name,
					filename_pattern: data.filename_pattern,
					sequence_name_template: data.sequence_name_template,
					shot_name_template: data.shot_name_template,
				};
			}
		} catch (e) {
			console.error(e);
		}

		// 글로벌 FTP 접속 설정은 항상 로드 (Browse 버튼에 필요)
		try {
			const res = await fetch("/system/config/ftp");
			if (res.ok) {
				const data = await res.json();
				ftpConfig = {
					enabled: data.enabled ?? false,
					protocol: data.protocol ?? "sftp",
					host: data.host ?? "",
					port: data.port ?? 22,
					username: data.username ?? "",
					password: data.password ?? "",
					passive: data.passive ?? true,
				};
			}
		} catch (e) {
			console.error(e);
		}

		// 프로젝트별 FTP 루트 경로 로드
		if (selectedProjectId !== "global") {
			try {
				const res = await fetch(`/system/config/projects/${selectedProjectId}/ftp-root`);
				if (res.ok) {
					const data = await res.json();
					ftpRemoteRoot = data.remote_root ?? "/";
				}
			} catch (e) {
				ftpRemoteRoot = "/";
			}
		} else {
			ftpRemoteRoot = "/";
		}

		ftpTestResult = null;
	}

	async function saveConfig() {
		try {
			const url =
				selectedProjectId === "global"
					? "/system/config"
					: `/system/config/projects/${selectedProjectId}`;

			const [res] = await Promise.all([
				// 파일명 파싱 설정 저장
				fetch(url, {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(config),
				}),
				// 글로벌 FTP 접속 설정 저장 (항상)
				fetch("/system/config/ftp", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(ftpConfig),
				}),
				// 프로젝트별 FTP 루트 경로 저장 (프로젝트 선택 시만)
				...(selectedProjectId !== "global"
					? [fetch(`/system/config/projects/${selectedProjectId}/ftp-root`, {
						method: "POST",
						headers: { "Content-Type": "application/json" },
						body: JSON.stringify({ remote_root: ftpRemoteRoot }),
					})]
					: []),
			]);

			if (res.ok) {
				message = `${selectedProjectId === "global" ? "Global" : "Project"} configuration saved successfully!`;
				setTimeout(() => (message = ""), 3000);
			} else {
				message = "Failed to save configuration.";
			}
		} catch (e) {
			message = "Error saving configuration.";
		}
	}

	async function testFtpConnection() {
		ftpTesting = true;
		ftpTestResult = null;
		try {
			const res = await fetch("/ftp/test", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(ftpConfig),
			});
			if (res.ok) {
				ftpTestResult = { ok: true, message: "Connection successful!" };
			} else {
				const data = await res.json();
				ftpTestResult = { ok: false, message: data.detail || "Connection failed" };
			}
		} catch (e: any) {
			ftpTestResult = { ok: false, message: e.message };
		} finally {
			ftpTesting = false;
		}
	}

	function handleFtpProtocolChange() {
		ftpConfig.port = ftpConfig.protocol === "sftp" ? 22 : 21;
	}

	async function testParse() {
		try {
			const res = await fetch("/system/preview-parse", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					filename: previewFilename,
					project_id:
						selectedProjectId === "global"
							? null
							: selectedProjectId,
					filename_pattern: config.filename_pattern,
					sequence_name_template: config.sequence_name_template,
					shot_name_template: config.shot_name_template,
				}),
			});
			const data = await res.json();
			previewResult = data;
		} catch (e) {
			console.error(e);
		}
	}

	function handleProjectChange(e: Event) {
		const target = e.target as HTMLSelectElement;
		selectedProjectId = target.value;
		loadConfig();
		previewResult = null;
	}
</script>

<div
	class="min-h-screen bg-slate-950 font-sans text-slate-100 selection:bg-blue-500 selection:text-white"
>
	<nav
		class="bg-slate-900/50 backdrop-blur-md border-b border-slate-800 px-6 py-4 sticky top-0 z-20"
	>
		<div class="max-w-7xl mx-auto flex justify-between items-center">
			<button
				class="flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity"
				onclick={() => goto("/publish")}
			>
				<img
					src={logo}
					alt="Logo"
					class="w-8 h-8 object-contain drop-shadow-md"
				/>
				<h1 class="font-bold text-lg tracking-tight">
					Kitsu Publisher
				</h1>
			</button>
			<div class="flex items-center gap-4 text-sm">
				<button
					onclick={() => goto("/publish")}
					class="text-slate-400 hover:text-white font-medium transition-colors"
					>Back to Publish</button
				>
			</div>
		</div>
	</nav>

	<main class="max-w-3xl mx-auto px-6 py-8 space-y-8">
		<header class="mb-8 flex justify-between items-end">
			<div>
				<h2 class="text-2xl font-bold text-white mb-2">Settings</h2>
				<p class="text-slate-400 text-sm">
					Configure how files are parsed and matched.
				</p>
			</div>
			<div class="w-64">
				<label
					class="block text-xs font-semibold text-slate-500 mb-1 uppercase tracking-wider"
					for="project-select">Target Project</label
				>
				<select
					id="project-select"
					class="w-full bg-slate-800 border border-slate-700 text-slate-200 rounded-xl px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none transition-all"
					onchange={handleProjectChange}
				>
					<option value="global">Global Settings (Default)</option>
					<optgroup label="Specific Projects">
						{#each projects as project}
							<option
								value={project.id}
								selected={selectedProjectId === project.id}
								>{project.name}</option
							>
						{/each}
					</optgroup>
				</select>
			</div>
		</header>

		<section
			class="bg-slate-900 rounded-2xl shadow-xl border border-slate-800 p-6 space-y-6 relative overflow-hidden"
		>
			{#if selectedProjectId !== "global"}
				<div
					class="absolute top-0 right-0 bg-blue-600/10 text-blue-400 text-[10px] font-bold px-3 py-1 rounded-bl-lg border-b border-l border-blue-600/20 uppercase tracking-tighter"
				>
					Project Specific
				</div>
			{/if}

			<div class="space-y-4">
				<div>
					<label
						class="block text-sm font-semibold text-slate-300 mb-1"
						for="default-task">Default Task Name</label
					>
					<p class="text-xs text-slate-500 mb-2">
						Used when the task name cannot be determined from the
						filename.
					</p>
					<input
						id="default-task"
						type="text"
						bind:value={config.default_task_name}
						class="w-full bg-slate-800 border border-slate-700 text-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none transition-all"
					/>
				</div>

				<div class="border-t border-slate-800 pt-4">
					<label
						class="block text-sm font-semibold text-slate-300 mb-1"
						for="filename-pattern">Filename Parsing Pattern</label
					>
					<p class="text-xs text-slate-500 mb-2">
						Define the structure of your filenames using <code
							>{`{variable}`}</code
						>
						placeholders. <br />
						Available variables: <code>episode</code>,
						<code>sequence</code>, <code>shot</code>,
						<code>task</code>, <code>version</code>. <br />
						Use <code>*</code> as a wildcard for optional suffixes
						(e.g., <code>_linear</code>), and <code>[]</code> for optional
						parts.
					</p>
					<input
						id="filename-pattern"
						type="text"
						bind:value={config.filename_pattern}
						class="w-full font-mono text-sm bg-slate-800 border border-slate-700 text-yellow-400 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none transition-all"
					/>
					<div
						class="mt-2 text-xs text-slate-500 bg-slate-950/50 p-3 rounded-lg border border-slate-800 space-y-1"
					>
						<p>
							Example 1: <code
								>{`{sequence}_{shot}_{task}_v{version}`}</code
							>
							matches <code>SQ01_SH010_Comp_v001</code>
						</p>
						<p>
							Example 2: <code
								>{`[{episode}_]{sequence}_{shot}*`}</code
							>
							matches <code>EP01_SQ01_SH010_v01_linear</code>
						</p>
					</div>
				</div>

				<div>
					<label
						class="block text-sm font-semibold text-slate-300 mb-1"
						for="seq-template">Sequence Name Construction</label
					>
					<p class="text-xs text-slate-500 mb-2">
						How Kitsu sequence names should be formed. Use <code
							>{`{episode}`}</code
						> if needed.
					</p>
					<input
						id="seq-template"
						type="text"
						bind:value={config.sequence_name_template}
						class="w-full font-mono text-sm bg-slate-800 border border-slate-700 text-pink-400 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none transition-all"
					/>
				</div>

				<div>
					<label
						class="block text-sm font-semibold text-slate-300 mb-1"
						for="shot-template">Shot Name Construction</label
					>
					<p class="text-xs text-slate-500 mb-2">
						How Kitsu shot names should be formed from the parsed
						variables.
					</p>
					<input
						id="shot-template"
						type="text"
						bind:value={config.shot_name_template}
						class="w-full font-mono text-sm bg-slate-800 border border-slate-700 text-green-400 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none transition-all"
					/>
				</div>
			</div>
		</section>

		<section
			class="bg-slate-900 rounded-2xl shadow-xl border border-slate-800 p-6"
		>
			<h3
				class="text-lg font-bold text-white mb-4 flex items-center gap-2"
			>
				<svg
					class="w-5 h-5 text-blue-500"
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
					><path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M19.428 15.428a2 2 0 00-1.022-.547l-2.384-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
					/></svg
				>
				Test Configuration
			</h3>
			<div class="flex gap-2 mb-4">
				<input
					type="text"
					bind:value={previewFilename}
					class="flex-1 bg-slate-800 border border-slate-700 text-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none transition-all placeholder-slate-600"
					placeholder="Enter a filename to test..."
				/>
				<button
					onclick={testParse}
					class="bg-slate-700 hover:bg-slate-600 text-white font-medium px-6 py-3 rounded-xl transition-all"
					>Test</button
				>
			</div>

			{#if previewResult}
				<div
					class="bg-slate-950 rounded-xl p-4 border border-slate-800 animate-in fade-in"
				>
					{#if previewResult.success}
						<div class="grid grid-cols-2 gap-4 text-sm">
							<div class="text-slate-500">
								Episode: <span class="text-slate-200"
									>{previewResult.data.episode_name ||
										"-"}</span
								>
							</div>
							<div class="text-slate-500">
								Sequence: <span class="text-slate-200"
									>{previewResult.data.sequence_name}</span
								>
							</div>
							<div class="text-slate-500">
								Shot Name: <span
									class="text-green-400 font-bold"
									>{previewResult.data.shot_name}</span
								>
							</div>
							<div class="text-slate-500">
								Task: <span class="text-blue-400"
									>{previewResult.data.task_name}</span
								>
							</div>
							<div class="text-slate-500">
								Version: <span class="text-purple-400"
									>v{previewResult.data.version}</span
								>
							</div>
						</div>
					{:else}
						<div class="text-red-400 flex items-center gap-2">
							<svg
								class="w-5 h-5"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
								><path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
								/></svg
							>
							{previewResult.message}
						</div>
					{/if}
				</div>
			{/if}
		</section>

		<!-- FTP/SFTP Settings -->
		<section class="bg-slate-900 rounded-2xl shadow-xl border border-slate-800 p-6 space-y-5 relative overflow-hidden">
			<div class="absolute top-0 right-0 bg-emerald-600/10 text-emerald-400 text-[10px] font-bold px-3 py-1 rounded-bl-lg border-b border-l border-emerald-600/20 uppercase tracking-tighter">
				FTP / SFTP
			</div>

			<div class="flex items-center justify-between">
				<div>
					<h3 class="text-base font-bold text-white">File Transfer Settings</h3>
					<p class="text-xs text-slate-500 mt-0.5">모든 프로젝트가 공유하는 FTP 서버 접속 정보입니다.</p>
				</div>
				<label class="flex items-center gap-3 cursor-pointer">
					<span class="text-sm text-slate-400">Enable FTP Transfer</span>
					<div
						onclick={() => (ftpConfig.enabled = !ftpConfig.enabled)}
						class="relative w-11 h-6 rounded-full transition-colors cursor-pointer {ftpConfig.enabled ? 'bg-emerald-600' : 'bg-slate-700'}"
					>
						<div class="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform {ftpConfig.enabled ? 'translate-x-5' : ''}"></div>
					</div>
				</label>
			</div>

			{#if ftpConfig.enabled}
				<div class="grid grid-cols-2 gap-4">
					<!-- Protocol -->
					<div class="col-span-2 sm:col-span-1">
						<label class="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">Protocol</label>
						<select
							bind:value={ftpConfig.protocol}
							onchange={handleFtpProtocolChange}
							class="w-full bg-slate-800 border border-slate-700 text-slate-200 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-emerald-500 outline-none transition-all"
						>
							<option value="sftp">SFTP (SSH, port 22)</option>
							<option value="ftp">FTP (port 21)</option>
						</select>
					</div>

					<!-- Port -->
					<div class="col-span-2 sm:col-span-1">
						<label class="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">Port</label>
						<input
							type="number"
							bind:value={ftpConfig.port}
							class="w-full bg-slate-800 border border-slate-700 text-slate-200 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-emerald-500 outline-none transition-all"
						/>
					</div>

					<!-- Host -->
					<div class="col-span-2">
						<label class="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">Host / IP</label>
						<input
							type="text"
							bind:value={ftpConfig.host}
							placeholder="e.g. ftp.example.com or 192.168.1.100"
							class="w-full bg-slate-800 border border-slate-700 text-slate-200 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-emerald-500 outline-none transition-all placeholder-slate-600"
						/>
					</div>

					<!-- Username -->
					<div>
						<label class="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">Username</label>
						<input
							type="text"
							bind:value={ftpConfig.username}
							autocomplete="off"
							class="w-full bg-slate-800 border border-slate-700 text-slate-200 rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-emerald-500 outline-none transition-all"
						/>
					</div>

					<!-- Password -->
					<div>
						<label class="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">Password</label>
						<div class="relative">
							{#if showFtpPassword}
								<input type="text" bind:value={ftpConfig.password} autocomplete="off"
									class="w-full bg-slate-800 border border-slate-700 text-slate-200 rounded-xl px-4 py-2.5 pr-10 focus:ring-2 focus:ring-emerald-500 outline-none transition-all" />
							{:else}
								<input type="password" bind:value={ftpConfig.password} autocomplete="off"
									class="w-full bg-slate-800 border border-slate-700 text-slate-200 rounded-xl px-4 py-2.5 pr-10 focus:ring-2 focus:ring-emerald-500 outline-none transition-all" />
							{/if}
							<button type="button" onclick={() => (showFtpPassword = !showFtpPassword)}
								class="absolute inset-y-0 right-3 flex items-center text-slate-500 hover:text-slate-300 transition-colors">
								{#if showFtpPassword}
									<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" /></svg>
								{:else}
									<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
								{/if}
							</button>
						</div>
					</div>

					<!-- FTP passive mode -->
					{#if ftpConfig.protocol === "ftp"}
						<div class="col-span-2 flex items-center gap-3">
							<input type="checkbox" id="ftp-passive" bind:checked={ftpConfig.passive}
								class="rounded border-slate-700 bg-slate-800 text-emerald-600" />
							<label for="ftp-passive" class="text-sm text-slate-400">Use Passive Mode (PASV) — recommended for most servers</label>
						</div>
					{/if}
				</div>

				<!-- Test connection -->
				<div class="flex items-center gap-4 pt-1">
					<button
						onclick={testFtpConnection}
						disabled={ftpTesting || !ftpConfig.host || !ftpConfig.username}
						class="bg-slate-700 hover:bg-slate-600 text-white font-medium px-5 py-2 rounded-xl transition-all disabled:opacity-50 flex items-center gap-2 text-sm"
					>
						{#if ftpTesting}
							<div class="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
							Testing...
						{:else}
							<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
							Test Connection
						{/if}
					</button>
					{#if ftpTestResult}
						<div class="flex items-center gap-2 text-sm {ftpTestResult.ok ? 'text-emerald-400' : 'text-red-400'}">
							{#if ftpTestResult.ok}
								<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
							{:else}
								<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
							{/if}
							{ftpTestResult.message}
						</div>
					{/if}
				</div>

				<!-- 프로젝트별 루트 경로 (프로젝트 선택 시만 표시) -->
				{#if selectedProjectId !== "global"}
					<div class="border-t border-slate-800 pt-5">
						<label class="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">
							Project Upload Root Path
						</label>
						<p class="text-xs text-slate-500 mb-2">
							이 프로젝트의 기본 업로드 경로입니다. 전송 시 이 경로부터 탐색을 시작합니다.
						</p>
						<div class="flex gap-2">
							<input
								type="text"
								bind:value={ftpRemoteRoot}
								placeholder="/"
								class="flex-1 bg-slate-800 border border-slate-700 text-slate-200 font-mono text-sm rounded-xl px-4 py-2.5 focus:ring-2 focus:ring-emerald-500 outline-none transition-all placeholder-slate-600"
							/>
							<button
								onclick={() => (ftpTreeOpen = true)}
								disabled={!ftpConfig.host || !ftpConfig.username}
								title="Browse server to select root path"
								class="bg-slate-700 hover:bg-slate-600 disabled:opacity-40 text-slate-200 px-4 py-2.5 rounded-xl transition-all flex items-center gap-2 text-sm font-medium"
							>
								<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
								</svg>
								Browse
							</button>
						</div>
					</div>
				{/if}
			{/if}
		</section>

		<div class="flex justify-end pt-4">
			<button
				onclick={saveConfig}
				class="bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 px-8 rounded-xl shadow-lg transition-all active:scale-95"
			>
				Save {selectedProjectId === "global" ? "Global" : "Project"} Settings
			</button>
		</div>

		{#if message}
			<div
				class="fixed bottom-8 left-1/2 -translate-x-1/2 bg-slate-800/90 backdrop-blur text-white px-6 py-3 rounded-full shadow-2xl border border-slate-700 animate-in fade-in slide-in-from-bottom-4"
			>
				{message}
			</div>
		{/if}
	</main>
</div>

{#if ftpConfig.enabled && selectedProjectId !== "global"}
	<FtpTreeModal
		bind:isOpen={ftpTreeOpen}
		ftpConfig={ftpConfig}
		initialPath={ftpRemoteRoot || "/"}
		onConfirm={(path) => { ftpRemoteRoot = path; }}
	/>
{/if}
