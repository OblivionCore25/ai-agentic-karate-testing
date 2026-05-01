function fn() {
    var env = karate.env; // get java system property 'karate.env'
    karate.log('karate.env system property was:', env);
    
    if (!env) {
      env = 'dev'; // a custom 'default'
    }
    
    var config = { // base config JSON
      baseUrl: 'http://localhost:8080/api/v1'
    };
    
    if (env == 'staging') {
      config.baseUrl = 'https://staging.example.com/api/v1';
    } else if (env == 'e2e') {
      config.baseUrl = 'https://e2e.example.com/api/v1';
    }
    
    // ── Database connection for JDBC verification steps ──
    config.dbUrl = karate.properties['db.url'] || 'jdbc:postgresql://localhost:5434/orders_db';
    config.dbUser = karate.properties['db.user'] || 'karate';
    config.dbPassword = karate.properties['db.password'] || 'karate_pass';
    config.dbDriverClassName = 'org.postgresql.Driver';
    
    // don't waste time waiting for a connection or if servers don't respond within 5 seconds
    karate.configure('connectTimeout', 5000);
    karate.configure('readTimeout', 5000);
    
    return config;
  }
