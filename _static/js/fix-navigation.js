// Copyright (C) 2024, 2025 Oracle and/or its affiliates.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

document.addEventListener('DOMContentLoaded', function() {
    // Find all navigation links
    const navLinks = document.querySelectorAll('.nav-link');

    // Loop through them to find the _INDEX link
    navLinks.forEach(function(link) {
      if (link.textContent.trim() === '_INDEX') {
        // Get the parent li element
        const listItem = link.closest('li');

        // Remove the _INDEX item from the navigation
        if (listItem) {
          listItem.remove();
        }
      }
    });

    const prevNextTitles = document.querySelectorAll('.prev-next-title');
    prevNextTitles.forEach(function(title) {
      if (title.textContent.trim() === '<no title>') {
        const linkElement = title.closest('a.right-next, a.left-prev');
        if (linkElement) linkElement.style.display = 'none';
      }
    });
  });
