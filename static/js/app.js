(function() {
    'use strict';
    
    var API = {
        get: function(url) {
            return fetch(url).then(function(r) {
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.json();
            });
        },
        
        post: function(url, data) {
            return fetch(url, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            }).then(function(r) {
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.json();
            });
        },
        
        put: function(url, data) {
            return fetch(url, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            }).then(function(r) {
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.json();
            });
        },
        
        del: function(url) {
            return fetch(url, {
                method: 'DELETE'
            }).then(function(r) {
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.json();
            });
        }
    };
    
    var UI = {
        alert: function(msg) {
            window.alert(msg);
        },
        
        confirm: function(msg) {
            return window.confirm(msg);
        },
        
        prompt: function(msg, def) {
            return window.prompt(msg, def || '');
        },
        
        redirect: function(url) {
            window.location.href = url;
        },
        
        open: function(url) {
            window.open(url);
        },
        
        reload: function() {
            window.location.reload();
        },
        
        getById: function(id) {
            return document.getElementById(id);
        },
        
        queryAll: function(sel) {
            return document.querySelectorAll(sel);
        },
        
        addClass: function(el, cls) {
            el.classList.add(cls);
        },
        
        removeClass: function(el, cls) {
            el.classList.remove(cls);
        },
        
        setText: function(el, txt) {
            el.textContent = txt;
        },
        
        setHtml: function(el, html) {
            el.innerHTML = html;
        }
    };
    
    var Store = {
        get: function(key) {
            try {
                return JSON.parse(localStorage.getItem(key));
            } catch (e) {
                return null;
            }
        },
        
        set: function(key, val) {
            localStorage.setItem(key, JSON.stringify(val));
        },
        
        remove: function(key) {
            localStorage.removeItem(key);
        }
    };
    
    window.AppAPI = API;
    window.AppUI = UI;
    window.AppStore = Store;
})();
