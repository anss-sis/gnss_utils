# gnss_utils
## IGSSiteParser
A simple parser to read IGS SiteLog into a Python OrderedDict

### Example usage
  - To do a quick test
      ```
       python3 igs_site_log_parser.py <path to IGS SiteLog file>
      ```
  
  - To use it in your code
       ```
       from igs_site_log_parser import IGSSiteLogParser
       slparser = IGSSiteLogParser()
       slparser.loadFromFile(filepathname)
       content = slparser.getContent()
       ```
    


