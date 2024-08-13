module.exports = {
    apps: [
      {
        name: 'akari',
        script: 'python3.12',
        args: 'main.py',
        interpreter: 'none', // This tells PM2 not to use Node.js to run the script
      },
      {
        name: 'lavalink',
        script: 'java',
        args: '-jar Lavalink.jar',
        interpreter: 'none', // This tells PM2 not to use Node.js to run the script
      }
    ],
  };
