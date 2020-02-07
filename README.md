# wwu_spec
WWU Vis-NIR spectrographic database

## patch notes

### v 0.2 (2/7/2020)
* Changes from items discussed in 2/3 meeting
* Added handling for uploaded files with multiple reflectance columns
* Changed search to interpret multiple-word queries more loosely
  * For instance, the query 'basalt glass' in the sample name field returns all entries containing either 'basalt' OR glass in their sample name field
  * UNLESS a sample exists with the exact sample name basalt glass'
* Buggy buttons in results page fixed
* turning on simulated spectrum now continues to display lab spectrum by default (can still be toggled off)
* Changed visual design of simulated spectra for improved legibility in this mode
* 'Show points' mode active by default
* added tool to normalize all curves to 1 at a given wavelength 
  * (workflow: switching it on reveals an 'arm selection' switch, which must also be switched on to a normalization wavelength. Without this secondary mode, it becomes extremely irritating to try to do calculations &c in wavelength normalization mode)
* All calculations are constrained to operate only on a single spectrum
  * User attempts to place calculation anchors on separate spectra are ignored
* Simple band depth calculator rewritten. Now two modes:
  * Automatically finds local minimum
  * Calculates band depth at point selected by user
* filter sets added: Pathfinder IMP, MER Pancam, Mastcam-Z, Landsat OLI
* Added functionality for dynamically switching filter sets for simulations
* All filtersets now also save simulated spectra with no illumination (i.e., illumination = 1, reflectance = radiance at all points)
* 'Locator line’ changed to 'vertical line'
* Redesign of entire site in WWU identity colors
  * the only elements drawn with colors outside of the identity color palette are simulated spectra
* Redesigned about page

### v.0.1 (1/31/2020)
* First release of major application redesign.
* updated to python 3.x / django 3.x. Backend changes related to update not specified here in detail.
* Extensively refactored Python and JS code for maintainability and extensibility. Individual changes too numerous to list.
* Broad visual redesign.
* replaced postgreSQL with SQLite (more maintainable, portable, and performant for small database size with few concurrent users)Altered all existing database models; changes included fields inappropriately referring to 'mineral' properties to 'sample' or 'material' as appropriateimproved behavior of autocomplete dialogsmass sample type flagging actions replaced with broader mass editing functionalityadded image upload and processing functionality
* added associated image download and display functionality
* improved upload input processing and UX 
* added capability to insert filter sets and illumination conditions into database
* added tools for simulating spectra viewed through filter sets under specified illumination conditions
* added 'reset zoom' button in graph view
* added 'shrink' button in graph view for more working space
* improved scrolling and zoom behavior in graph view
* Fixed various bugs related to widget positioning in graph view
* Redesigned control interface and layout of graph view for improved usability and accessibility
* fixed a bug related to graph boundary setting when graphing multiple spectra
* added calculators for simple band depth, ratio, and slope in graph view
* added option to drop multiple vertical lines in graph view
* added option to linearly peak-normalize spectra to 1 in graph view
* added option to y-offset spectra in graph view
* added user-facing bulk-upload capability
* advanced search replaced with 'any' field 
* results view redesigned to reduce amount of data presented to users for improved readability and navigation
