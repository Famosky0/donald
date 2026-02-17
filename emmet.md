Emmet Cheat Sheet (HTML / Tailwind)

This is a clean, structured reference you can come back to anytime. Emmet is about speed + structure. Mastering this lets you build layouts in seconds instead of minutes.

⸻

1. Core Idea

Emmet syntax = HTML structure in one line

Symbol Meaning
tag HTML element
. class

# id

>     child (nesting)

- sibling

* multiplication
  $ numbering
  {} text content
  [] attributes
  () grouping
  ^ climb up one level

⸻

2. Basic Elements & Classes

section.box\*6

<section class="box"></section> <!-- x6 -->

li.box\*6

<li class="box"></li> <!-- x6 -->

.box\*6

<div class="box"></div> <!-- x6 -->

⸻

3. Nesting (THIS is where people get good)

ul>li.box\*6

<ul>
  <li class="box"></li>
  <li class="box"></li>
  <li class="box"></li>
  <li class="box"></li>
  <li class="box"></li>
  <li class="box"></li>
</ul>

Think visual hierarchy while typing.

⸻

4. Numbered Classes (Used constantly)

.box$\*6

<div class="box1"></div>
<div class="box2"></div>
<div class="box3"></div>
<div class="box4"></div>
<div class="box5"></div>
<div class="box6"></div>

🔥 Pro tip: great for grids, cards, placeholders.

⸻

5. Attributes + Content

button.btn{Click}\*3

<button class="btn">Click</button>
<button class="btn">Click</button>
<button class="btn">Click</button>

⸻

6. Class + ID Combo

div.card#main

<div class="card" id="main"></div>

⸻

7. Child vs Sibling

Child (>)

div>p

<div>
  <p></p>
</div>

Sibling (+)

h1+p+button

<h1></h1>
<p></p>
<button></button>

⸻

8. Multiplication

.card\*4

<div class="card"></div> <!-- x4 -->

⸻

9. Text Content

button{Submit}

<button>Submit</button>

⸻

10. Attributes (Forms & Images)

input[type=email placeholder="Email"]

<input type="email" placeholder="Email">

img[src=avatar.png alt="Profile"]

<img src="avatar.png" alt="Profile">

⸻

11. Grouping (Complex Structures)

header>(h1+p)+nav>ul>li\*3

<header>
  <h1></h1>
  <p></p>
  <nav>
    <ul>
      <li></li>
      <li></li>
      <li></li>
    </ul>
  </nav>
</header>

This is real layout power.

⸻

12. Climb Up (^) — Advanced

div>p>span^button

<div>
  <p>
    <span></span>
  </p>
  <button></button>
</div>

Use this when layouts branch.

⸻

13. Tailwind = Emmet on steroids 🔥

div.flex.items-center.justify-between.p-4.bg-black.text-white

<div class="flex items-center justify-between p-4 bg-black text-white"></div>

⸻

14. Real TaskFlow-Style Example

.header.flex.items-center.justify-between.p-4.bg-black.text-white>
.brand>p{TaskFlow}

<div class="header flex items-center justify-between p-4 bg-black text-white">
  <div class="brand">
    <p>TaskFlow</p>
  </div>
</div>

⸻

15. Common Gotcha (IMPORTANT)

❌ This breaks:

p.text-[20px].text-white\*10

✅ Correct way:

p[class="text-[20px] text-white"]\*10

Emmet treats [] as literal attributes — required for Tailwind arbitrary values.

⸻

16. Mental Model (Memorize This)

Write structure first, style second.

If you can say the layout out loud, you can write it in Emmet.

⸻

17. Mastery Path
    1.  Simple elements
    2.  Nesting (> + +)
    3.  Grouping (())
    4.  Numbering ($)
    5.  Tailwind arbitrary values ([])

Once this clicks, HTML becomes muscle memory.
