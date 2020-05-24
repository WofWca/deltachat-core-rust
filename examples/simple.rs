use tempfile::tempdir;

use deltachat::chat;
use deltachat::chatlist::*;
use deltachat::config;
use deltachat::contact::*;
use deltachat::context::*;
use deltachat::Event;

fn cb(event: Event) {
    match event {
        Event::ConfigureProgress(progress) => {
            log::info!("progress: {}", progress);
        }
        Event::Info(msg) => {
            log::info!("{}", msg);
        }
        Event::Warning(msg) => {
            log::warn!("{}", msg);
        }
        Event::Error(msg) | Event::ErrorNetwork(msg) => {
            log::error!("{}", msg);
        }
        event => {
            log::info!("{:?}", event);
        }
    }
}

/// Run with `RUST_LOG=simple=info cargo run --release --example simple --features repl -- email pw`.
#[async_std::main]
async fn main() {
    pretty_env_logger::try_init_timed().ok();

    let dir = tempdir().unwrap();
    let dbfile = dir.path().join("db.sqlite");
    log::info!("creating database {:?}", dbfile);
    let ctx = Context::new("FakeOs".into(), dbfile.into())
        .await
        .expect("Failed to create context");
    let info = ctx.get_info().await;
    log::info!("info: {:#?}", info);

    let events = ctx.get_event_emitter();
    let events_spawn = async_std::task::spawn(async move {
        while let Some(event) = events.recv().await {
            cb(event);
        }
    });

    log::info!("configuring");
    let args = std::env::args().collect::<Vec<String>>();
    assert_eq!(args.len(), 3, "requires email password");
    let email = args[1].clone();
    let pw = args[2].clone();
    ctx.set_config(config::Config::Addr, Some(&email))
        .await
        .unwrap();
    ctx.set_config(config::Config::MailPw, Some(&pw))
        .await
        .unwrap();

    ctx.configure().await.unwrap();

    log::info!("------ RUN ------");
    ctx.start_io().await;
    log::info!("--- SENDING A MESSAGE ---");

    let contact_id = Contact::create(&ctx, "dignifiedquire", "dignifiedquire@gmail.com")
        .await
        .unwrap();
    let chat_id = chat::create_by_contact_id(&ctx, contact_id).await.unwrap();

    for i in 0..2 {
        chat::send_text_msg(&ctx, chat_id, format!("Hi, here is my {}nth message!", i))
            .await
            .unwrap();
    }

    log::info!("fetching chats..");
    let chats = Chatlist::try_load(&ctx, 0, None, None).await.unwrap();

    for i in 0..chats.len() {
        let summary = chats.get_summary(&ctx, 0, None).await;
        let text1 = summary.get_text1();
        let text2 = summary.get_text2();
        log::info!("chat: {} - {:?} - {:?}", i, text1, text2,);
    }

    log::info!("stopping");
    ctx.stop_io().await;
    log::info!("closing");
    drop(ctx);
    events_spawn.await;
}
