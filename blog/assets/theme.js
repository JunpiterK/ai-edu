(function(){
  var STORAGE_KEY = 'ai-edu-theme';
  var root = document.documentElement;
  var meta = document.querySelector('meta[name="theme-color"]');
  var lightColor = '#F4F7F9';
  var darkColor = '#08131E';

  function preferredTheme(){
    try{
      var saved = localStorage.getItem(STORAGE_KEY);
      if(saved === 'light' || saved === 'dark') return saved;
    }catch(e){}
    if(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';
    return 'light';
  }

  function applyTheme(theme){
    root.setAttribute('data-theme', theme);
    root.style.colorScheme = theme;
    if(meta) meta.setAttribute('content', theme === 'dark' ? darkColor : lightColor);
    document.querySelectorAll('[data-theme-toggle]').forEach(function(button){
      var isDark = theme === 'dark';
      button.setAttribute('aria-pressed', isDark ? 'true' : 'false');
      button.setAttribute('aria-label', isDark ? 'Switch to light theme' : 'Switch to dark theme');
      button.setAttribute('title', isDark ? 'Light theme' : 'Dark theme');
      var label = button.querySelector('.theme-toggle-label');
      if(label) label.textContent = isDark ? 'Light' : 'Dark';
    });
  }

  function saveTheme(theme){
    try{ localStorage.setItem(STORAGE_KEY, theme); }catch(e){}
  }

  function installToggle(){
    if(document.querySelector('[data-theme-toggle]')) return;
    var nav = document.querySelector('.nav-links');
    if(!nav) return;

    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'theme-toggle';
    button.setAttribute('data-theme-toggle', '');
    button.innerHTML = '<span class="theme-toggle-track" aria-hidden="true"><span class="theme-toggle-knob"></span></span><span class="theme-toggle-label">Dark</span>';

    var languageSwitch = nav.querySelector('.language-switch');
    if(languageSwitch && languageSwitch.nextSibling){
      nav.insertBefore(button, languageSwitch.nextSibling);
    }else{
      nav.appendChild(button);
    }

    button.addEventListener('click', function(){
      var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      applyTheme(next);
      saveTheme(next);
    });
  }

  applyTheme(preferredTheme());

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', function(){
      installToggle();
      applyTheme(root.getAttribute('data-theme') || preferredTheme());
    });
  }else{
    installToggle();
    applyTheme(root.getAttribute('data-theme') || preferredTheme());
  }

  if(window.location.hash){
    var target = document.getElementById(window.location.hash.slice(1));
    if(target && target.closest('.pypi-walkthrough')){
      var anchorTimer;
      var anchorCancelled = false;

      function alignWalkthroughAnchor(delay){
        window.clearTimeout(anchorTimer);
        anchorTimer = window.setTimeout(function(){
          if(!anchorCancelled) target.scrollIntoView({block: 'start'});
        }, delay);
      }

      ['pointerdown', 'touchstart', 'wheel', 'keydown'].forEach(function(eventName){
        window.addEventListener(eventName, function(){
          anchorCancelled = true;
          window.clearTimeout(anchorTimer);
        }, {once: true, passive: true});
      });

      target.closest('.pypi-walkthrough').querySelectorAll('img').forEach(function(image){
        if(!image.complete) image.addEventListener('load', function(){ alignWalkthroughAnchor(80); }, {once: true});
      });

      window.addEventListener('load', function(){ alignWalkthroughAnchor(250); }, {once: true});
      if(document.fonts && document.fonts.ready){
        document.fonts.ready.then(function(){ alignWalkthroughAnchor(80); });
      }
    }
  }
})();
