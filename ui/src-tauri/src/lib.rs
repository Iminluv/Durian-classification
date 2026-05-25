use tauri_plugin_shell::ShellExt;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_shell::init())
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      
      // Spawn python backend sidecar
      let app_handle = app.handle().clone();
      tauri::async_runtime::spawn(async move {
        if let Ok(sidecar) = app_handle.shell().sidecar("durian-backend") {
          match sidecar.spawn() {
            Ok((mut rx, _tx)) => {
              println!("Successfully spawned durian-backend sidecar.");
              while let Some(event) = rx.recv().await {
                match event {
                  tauri_plugin_shell::process::CommandEvent::Stdout(line) => {
                    println!("[Backend Stdout]: {}", String::from_utf8_lossy(&line).trim());
                  }
                  tauri_plugin_shell::process::CommandEvent::Stderr(line) => {
                    eprintln!("[Backend Stderr]: {}", String::from_utf8_lossy(&line).trim());
                  }
                  _ => {}
                }
              }
            }
            Err(e) => {
              eprintln!("Failed to spawn durian-backend sidecar: {:?}", e);
            }
          }
        } else {
          eprintln!("durian-backend sidecar configuration not found.");
        }
      });
      
      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
