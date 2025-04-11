module.exports = {
    apps: [
      {
        name: "celery_worker",
        script: "cmd",
        args: "/c celery -A AMS worker --loglevel=info --pool=solo",
        watch: false
      }
    ]
  };
  