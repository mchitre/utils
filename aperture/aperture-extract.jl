using PLists

cd(@__DIR__)

## settings
DB_NAME = "ApertureData.xml"
MAX_ALBUM_SIZE = 10000
OUTPUT_DIR = "Albums"
SHELL_SCRIPT = "extract.sh"

## compose shell script to extract images
db = read_xml_plist(DB_NAME)
img = db["Master Image List"]
open(SHELL_SCRIPT, "w") do io
  for album ∈ db["List of Albums"]
    if "KeyList" ∈ keys(album)
      length(album["KeyList"]) > MAX_ALBUM_SIZE && continue
      albumname = album["AlbumName"]
      first = true
      for k ∈ album["KeyList"]
        m = match(r"^.*/(Previews/.*)$", img[k]["ImagePath"])
        if m !== nothing && isfile(m[1])
          filename = splitpath(m[1])[end]
          outalbumname = replace(albumname, "&amp;" => "&", "&apos;" => "'")
          first && println(io, "mkdir -p \"$(OUTPUT_DIR)/$(outalbumname)\"")
          println(io, "cp \"$(m[1])\" \"$(OUTPUT_DIR)/$(outalbumname)/$(filename)\"")
          first = false
        end
      end
    end
  end
end
