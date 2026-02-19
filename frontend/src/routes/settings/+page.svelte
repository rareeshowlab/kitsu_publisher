<script lang="ts">
	import { onMount } from "svelte";
	import { goto } from "$app/navigation";
	import logo from "$lib/assets/logo.png";

	let config = $state({
		default_task_name: "Compositing",
		filename_pattern: "{episode}_{sequence}_{shot}_{task}_v{version}",
		sequence_name_template: "{episode}_{sequence}",
		shot_name_template: "{episode}_{sequence}_{shot}",
	});

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
		try {
			const url =
				selectedProjectId === "global"
					? "/system/config"
					: `/system/config/projects/${selectedProjectId}`;

			const res = await fetch(url);
			if (res.ok) {
				const data = await res.json();
				// 전역 설정 로드 시 project_settings는 UI에 안 보이게 필터링 필요할 수도 있지만 ConfigModel 스키마에 맞춰서 처리
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
	}

	async function saveConfig() {
		try {
			const url =
				selectedProjectId === "global"
					? "/system/config"
					: `/system/config/projects/${selectedProjectId}`;

			const res = await fetch(url, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(config),
			});
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
