module.exports = {
  apps: [{
    name: "telegram-bot",
    script: "python",
    args: "main1.py",
    env: {
      PYTHONUNBUFFERED: "1"
    },
    restart_delay: 4000,
    max_restarts: 10,
    watch: false
  }]
};
