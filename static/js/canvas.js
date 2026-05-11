(function() {
    'use strict';
    
    var CanvasHelper = {
        clear: function(ctx, width, height) {
            ctx.clearRect(0, 0, width, height);
        },
        
        fill: function(ctx, color, width, height) {
            ctx.fillStyle = color;
            ctx.fillRect(0, 0, width, height);
        },
        
        line: function(ctx, x1, y1, x2, y2, color, width) {
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.strokeStyle = color;
            ctx.lineWidth = width;
            ctx.stroke();
        },
        
        rect: function(ctx, x, y, w, h, fill, stroke) {
            if (fill) {
                ctx.fillStyle = fill;
                ctx.fillRect(x, y, w, h);
            }
            if (stroke) {
                ctx.strokeStyle = stroke;
                ctx.strokeRect(x, y, w, h);
            }
        },
        
        arc: function(ctx, x, y, r, start, end, color, width) {
            ctx.beginPath();
            ctx.arc(x, y, r, start, end);
            ctx.strokeStyle = color;
            ctx.lineWidth = width;
            ctx.stroke();
        },
        
        text: function(ctx, txt, x, y, color, size) {
            ctx.fillStyle = color;
            ctx.font = size + 'px Arial';
            ctx.fillText(txt, x, y);
        },
        
        snap: function(val, grid) {
            return Math.round(val / grid) * grid;
        },
        
        dist: function(x1, y1, x2, y2) {
            var dx = x2 - x1;
            var dy = y2 - y1;
            return Math.sqrt(dx * dx + dy * dy);
        },
        
        pointLineDist: function(px, py, x1, y1, x2, y2) {
            var A = px - x1;
            var B = py - y1;
            var C = x2 - x1;
            var D = y2 - y1;
            var dot = A * C + B * D;
            var lenSq = C * C + D * D;
            var param = -1;
            if (lenSq !== 0) param = dot / lenSq;
            var xx, yy;
            if (param < 0) {
                xx = x1;
                yy = y1;
            } else if (param > 1) {
                xx = x2;
                yy = y2;
            } else {
                xx = x1 + param * C;
                yy = y1 + param * D;
            }
            var dx = px - xx;
            var dy = py - yy;
            return Math.sqrt(dx * dx + dy * dy);
        }
    };
    
    window.CanvasHelper = CanvasHelper;
})();
