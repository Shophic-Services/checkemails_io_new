

 (function ($) {
    let ID = "span-check";
  
    let HighlightWithinTextarea = function ($el, config) {
      this.init($el, config);
    };
  
    HighlightWithinTextarea.prototype = {
      init: function ($el, config) {
        this.$el = $el;
  
        // backwards compatibility with v1 (deprecated)
        if (this.getType(config) === "function") {
          config = { highlight: config };
        }
  
        if (this.getType(config) === "custom") {
          this.highlight = config;
          this.generate();
        } else {
          console.error("valid config object not provided");
        }
      },
  
      // returns identifier strings that aren't necessarily "real" JavaScript types
      getType: function (instance) {
        let type = typeof instance;
        if (!instance) {
          return "falsey";
        } else if (Array.isArray(instance)) {
          if (instance.length === 2 && typeof instance[0] === "number" && typeof instance[1] === "number") {
            return "range";
          } else {
            return "array";
          }
        } else if (type === "object") {
          if (instance instanceof RegExp) {
            return "regexp";
          } else if (instance.hasOwnProperty("highlight")) {
            return "custom";
          }
        } else if (type === "function" || type === "string") {
          return type;
        }
  
        return "other";
      },
  
      generate: function () {
        this.$el
          .addClass(ID + "-input " + ID + "-content")
          .on("input." + ID, this.handleInput.bind(this))
          .on("scroll." + ID, this.handleScroll.bind(this));
  
        this.$highlights = $("<div>", { class: ID + "-highlights " + ID + "-content" });
  
        this.$backdrop = $("<div>", { class: ID + "-backdrop" }).append(this.$highlights);
  
        this.$container = $("<div>", { class: ID + "-container" })
          .insertAfter(this.$el)
          .append(this.$backdrop, this.$el) // moves $el into $container
          .on("scroll", this.blockContainerScroll.bind(this));
  
        this.browser = this.detectBrowser();
        switch (this.browser) {
          case "firefox":
            this.fixFirefox();
            break;
          case "ios":
            this.fixIOS();
            break;
        }
  
        // plugin function checks this for success
        this.isGenerated = true;
  
        // trigger input event to highlight any existing input
        this.handleInput();
      },
  
      // browser sniffing sucks, but there are browser-specific quirks to handle
      // that are not a matter of feature detection
      detectBrowser: function () {
        let ua = window.navigator.userAgent.toLowerCase();
        if (ua.indexOf("firefox") !== -1) {
          return "firefox";
        } else if (!!ua.match(/msie|trident\/7|edge/)) {
          return "ie";
        } else if (!!ua.match(/ipad|iphone|ipod/) && ua.indexOf("windows phone") === -1) {
          // Windows Phone flags itself as "like iPhone", thus the extra check
          return "ios";
        } else {
          return "other";
        }
      },
  
      // Firefox doesn't show text that scrolls into the padding of a textarea, so
      // rearrange a couple box models to make highlights behave the same way
      fixFirefox: function () {
        // take padding and border pixels from highlights div
        let padding = this.$highlights.css(["padding-top", "padding-right", "padding-bottom", "padding-left"]);
        let border = this.$highlights.css([
          "border-top-width",
          "border-right-width",
          "border-bottom-width",
          "border-left-width",
        ]);
        this.$highlights.css({
          padding: "0",
          "border-width": "0",
        });
  
        this.$backdrop
          .css({
            // give padding pixels to backdrop div
            "margin-top": "+=" + padding["padding-top"],
            "margin-right": "+=" + padding["padding-right"],
            "margin-bottom": "+=" + padding["padding-bottom"],
            "margin-left": "+=" + padding["padding-left"],
          })
          .css({
            // give border pixels to backdrop div
            "margin-top": "+=" + border["border-top-width"],
            "margin-right": "+=" + border["border-right-width"],
            "margin-bottom": "+=" + border["border-bottom-width"],
            "margin-left": "+=" + border["border-left-width"],
          });
      },
  
      // iOS adds 3px of (unremovable) padding to the left and right of a textarea,
      // so adjust highlights div to match
      fixIOS: function () {
        this.$highlights.css({
          "padding-left": "+=3px",
          "padding-right": "+=3px",
        });
      },
  
      handleInput: function () {
        let input = this.$el.val();
        let ranges = this.getRanges(input, this.highlight);
        let unstaggeredRanges = this.removeStaggeredRanges(ranges);
        let boundaries = this.getBoundaries(unstaggeredRanges);
        this.renderMarks(boundaries);
        this.renderAside(boundaries);
      },
  
      getRanges: function (input, highlight) {
        let type = this.getType(highlight);
        switch (type) {
          case "array":
            return this.getArrayRanges(input, highlight);
          case "function":
            return this.getFunctionRanges(input, highlight);
          case "regexp":
            return this.getRegExpRanges(input, highlight);
          case "string":
            return this.getStringRanges(input, highlight);
          case "range":
            return this.getRangeRanges(input, highlight);
          case "custom":
            return this.getCustomRanges(input, highlight);
          default:
            if (!highlight) {
              // do nothing for falsey values
              return [];
            } else {
              console.error("unrecognized highlight type");
            }
        }
      },
  
      getArrayRanges: function (input, arr) {
        let ranges = arr.map(this.getRanges.bind(this, input));
        return Array.prototype.concat.apply([], ranges);
      },
  
      getFunctionRanges: function (input, func) {
        return this.getRanges(input, func(input));
      },
  
      getRegExpRanges: function (input, regex) {
        let ranges = [];
        let match;
        while (((match = regex.exec(input)), match !== null)) {
          ranges.push([match.index, match.index + match[0].length]);
          if (!regex.global) {
            // non-global regexes do not increase lastIndex, causing an infinite loop,
            // but we can just break manually after the first match
            break;
          }
        }
        return ranges;
      },
  
      getStringRanges: function (input, str) {
        let ranges = [];
        let inputLower = input.toLowerCase();
        let strLower = str.toLowerCase();
        let index = 0;
        while (((index = inputLower.indexOf(strLower, index)), index !== -1)) {
          ranges.push([index, index + strLower.length]);
          index += strLower.length;
        }
        return ranges;
      },
  
      getRangeRanges: function (input, range) {
        return [range];
      },
  
      getCustomRanges: function (input, custom) {
        let ranges = this.getRanges(input, custom.highlight);
  
        if (custom.category) {
          ranges.forEach(function (range) {
            // persist class name as a property of the array
            if (range.category) {
              range.category = custom.category + " " + range.category;
            } else {
              range.category = custom.category;
            }
  
            range.highlight = custom.highlight;
            range.keyword = custom.keyword;
          });
        }
  
        return ranges;
      },
  
      // prevent staggered overlaps (clean nesting is fine)
      removeStaggeredRanges: function (ranges) {
        let unstaggeredRanges = [];
        ranges.forEach(function (range) {
          let isStaggered = unstaggeredRanges.some(function (unstaggeredRange) {
            let isStartInside = range[0] > unstaggeredRange[0] && range[0] < unstaggeredRange[1];
            let isStopInside = range[1] > unstaggeredRange[0] && range[1] < unstaggeredRange[1];
            return isStartInside !== isStopInside; // xor
          });
          if (!isStaggered) {
            unstaggeredRanges.push(range);
          }
        });
        return unstaggeredRanges;
      },
  
      getBoundaries: function (ranges) {
        let boundaries = [];
        ranges.forEach(function (range) {
          // console.log(range);
          boundaries.push({
            type: "start",
            index: range[0],
            highlight: range.highlight,
            keyword: range.keyword,
            category: range.category,
          });
          boundaries.push({
            type: "stop",
            index: range[1],
          });
        });
  
        this.sortBoundaries(boundaries);
        return boundaries;
      },
  
      sortBoundaries: function (boundaries) {
        // backwards sort (since marks are inserted right to left)
        boundaries.sort(function (a, b) {
          if (a.index !== b.index) {
            return b.index - a.index;
          } else if (a.type === "stop" && b.type === "start") {
            return 1;
          } else if (a.type === "start" && b.type === "stop") {
            return -1;
          } else {
            return 0;
          }
        });
      },
  
      renderMarks: function (boundaries) {
        let input = this.$el.val();
        boundaries.forEach(function (boundary, index) {
          let markup;
          if (boundary.type === "start") {
            markup = "{{span-check-mark-start|" + index + "}}";
          } else {
            markup = "{{span-check-mark-stop}}";
          }
          input = input.slice(0, boundary.index) + markup + input.slice(boundary.index);
        });
  
        // this keeps scrolling aligned when input ends with a newline
        input = input.replace(/\n(\{\{span-check-mark-stop\}\})?$/, "\n\n$1");
  
        // encode HTML entities
        input = input.replace(/</g, "&lt;").replace(/>/g, "&gt;");
  
        if (this.browser === "ie") {
          // IE/Edge wraps whitespace differently in a div vs textarea, this fixes it
          input = input.replace(/ /g, " <wbr>");
        }
  
        // replace start tokens with opening <mark> tags with class name
        input = input.replace(/\{\{span-check-mark-start\|(\d+)\}\}/g, function (match, submatch) {
          var category = boundaries[+submatch].category;
          if (category) {
            return '<mark class="spam-category-' + category + '">';
          } else {
            return "<mark>";
          }
        });
  
        // replace stop tokens with closing </mark> tags
        input = input.replace(/\{\{span-check-mark-stop\}\}/g, "</mark>");
  
        this.$highlights.html(input);
      },
  
      renderAside: function (boundaries) {
        // Metadata
        const input = this.$el.val();
        const totalWords = input.split(/\s+/).length - 1;
        const readtime = Math.round(totalWords / 200);
  
        if (totalWords < 1) {
          $("#spam-checker-aside").html(
            `
            <ul class="list-group list-group-flush"><li class="list-group-item d-flex justify-content-between align-items-center">Word Count </li><li class="list-group-item d-flex justify-content-between align-items-center">Read time</li><li class="list-group-item d-flex justify-content-between align-items-center">Spam Words</li></ul>
            `
          );
          return;
        }
  
        let table = "";
  
        table += "<li class='list-group-item d-flex justify-content-between align-items-center'>Word Count <span class='badge bg-dark font-size-14'>" + totalWords + "</span></li>";
        table += "<li class='list-group-item d-flex justify-content-between align-items-center'>Read time <span class='badge bg-secondary font-size-14'>" + (readtime ? readtime + " min" : "a few seconds") + "</span></li>";
  
        // List categories
        const categories = {};
        let totalSpamHits = 0;
        boundaries.forEach((range) => {
          if (!range.category) {
            return;
          }
  
          const category = range.category;
          categories[category] = categories[category] || { type: category, keywords: [] };
          categories[category].keywords.push({ keyword: range.keyword });
  
          totalSpamHits++;
        });
  
        let list = "";
  
        for (const hash in categories) {
          const category = categories[hash];
          let categoryName = "";
  
          switch (category.type) {
            case "overcommit":
              categoryName = "<i class='uil uil-megaphone font-size-20 text-white'></i> Overcommit ";
              break;
            case "pushy":
              categoryName = "<i class='uil uil-bell font-size-20 text-white'></i> Pushy ";
              break;
            case "monetary":
              categoryName = "<i class='uil uil-usd-circle font-size-20 text-white'></i> Monetary ";
              break;
            case "crafty":
              categoryName = "<i class='uil uil-18-plus font-size-20 text-white'></i> Crafty ";
              break;
            case "notnatural":
              categoryName = "<i class='uil uil-robot font-size-20 text-white'></i> Not natural ";
              break;
            default:
              continue;
          }
  
          list +=
            "<li class='list-group-item spam-category-" +
            category.type +
            "'>" +
            categoryName +
            "<span>(" +
            category.keywords.length +
            ")</span></li>";
        }
  
        // Score (great, okay, poor)
        let score = totalSpamHits;
  
        if (categories["monetary"] || categories["crafty"]) {
          score += 20;
        }
  
        if (categories["pushy"] || categories["overcommit"]) {
          score += 10;
        }
  
        const scoreAsHtml =
          score > 20
            ? "<span class='badge bg-danger font-size-14'>Poor</span>"
            : score > 5
            ? "<span classs='badge bg-info font-size-14'>Okay</span>"
            : "<span class='badge bg-success font-size-14'>Great</span>";
        const scoretextAsHtml =
            score > 20
              ? "Poor"
              : score > 5
              ? "Okay"
              : "Great";
        const scorecolorAsHtml =
              score > 20
                ? "danger"
                : score > 5
                ? "warning"
                : "success";
        const score_html = `<div class="single-chart">
        <svg viewBox="0 0 36 36" class="circular-chart ` + scorecolorAsHtml +  `">
          <path class="circle-bg"
            d="M18 2.0845
              a 15.9155 15.9155 0 0 1 0 31.831
              a 15.9155 15.9155 0 0 1 0 -31.831"
          />
          <path class="circle"
            stroke-dasharray="100, 100"
            d="M18 2.0845
              a 15.9155 15.9155 0 0 1 0 31.831
              a 15.9155 15.9155 0 0 1 0 -31.831"
          />
          <text x="18" y="20.35" class="percentage">`+ scoretextAsHtml +`</text>
        </svg>
      </div>`
  
        table += "<li class='list-group-item d-flex justify-content-between align-items-center'>Spam Words <span class='badge bg-warning font-size-14'>" + totalSpamHits + "</span></li>";
        // table += "<li class='list-group-item d-flex justify-content-between align-items-center'>Score " + scoreAsHtml + "</li>";
  
        // Append to HTML
        list = `<ul class="list-group mt-3">${list}</ul>`;
        table = score_html + "<ul class='list-group list-group-flush'>" + table + "</ul>";
  
        $("#spam-checker-aside").html(table + list);
      },
  
      handleScroll: function () {
        let scrollTop = this.$el.scrollTop();
        this.$backdrop.scrollTop(scrollTop);
  
        // Chrome and Safari won't break long strings of spaces, which can cause
        // horizontal scrolling, this compensates by shifting highlights by the
        // horizontally scrolled amount to keep things aligned
        let scrollLeft = this.$el.scrollLeft();
        this.$backdrop.css("transform", scrollLeft > 0 ? "translateX(" + -scrollLeft + "px)" : "");
      },
  
      // in Chrome, page up/down in the textarea will shift stuff within the
      // container (despite the CSS), this immediately reverts the shift
      blockContainerScroll: function () {
        this.$container.scrollLeft(0);
      },
  
      destroy: function () {
        this.$backdrop.remove();
        this.$el
          .unwrap()
          .removeClass(ID + "-text " + ID + "-input")
          .off(ID)
          .removeData(ID);
      },
    };
  
    // register the jQuery plugin
    $.fn.highlightWithinTextarea = function (options) {
      return this.each(function () {
        let $this = $(this);
        let plugin = $this.data(ID);
  
        if (typeof options === "string") {
          if (plugin) {
            switch (options) {
              case "update":
                plugin.handleInput();
                break;
              case "destroy":
                plugin.destroy();
                break;
              default:
                console.error("unrecognized method string");
            }
          } else {
            console.error("plugin must be instantiated first");
          }
        } else {
          if (plugin) {
            plugin.destroy();
          }
          plugin = new HighlightWithinTextarea($this, options);
          if (plugin.isGenerated) {
            $this.data(ID, plugin);
          }
        }
      });
    };

  
    $(function () {
    dataset = $.map(JSON.parse($("#spam-checker-textarea").attr('data-spam-keyword')), function(element){
       if (element.highlight){

           return { highlight: new RegExp(element.highlight, "gi"), keyword: element.keyword, category: element.category_title }
       }
    })
      $("#spam-checker-textarea").highlightWithinTextarea({
        highlight: dataset,
      });
    });
  })(jQuery);
  