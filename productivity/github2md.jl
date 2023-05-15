using HTTP
using JSON3

### user settings

const AUTH = "~/.github2do/auth.txt"
const TASKDOC = "~/.github2do/tasks.md"

### Github API

const CREDS = open(expanduser(AUTH)) do f
  username = readline(f)
  creds = readline(f)
  "$username:$creds"
end

function urlwithcreds(url)
  parts = split(url, "://")
  insert!(parts, 2, "://$(CREDS)@")
  join(parts)
end

function querygithub(f)
  @info "https://api.github.com/issues"
  rsp = HTTP.get(urlwithcreds("https://api.github.com/issues"))
  spin = false
  while rsp.status == 200
    f(JSON3.read(String(rsp.body)))
    for hdr ∈ rsp.headers
      if lowercase(hdr[1]) == "link"
        links = split(hdr[2], ',')
        ndx = findfirst(link -> contains(link, ">; rel=\"next\""), links)
        if ndx !== nothing
          link = replace(first(split(links[ndx], ';')), r"[< >]" => "")
          @info link
          rsp = HTTP.get(urlwithcreds(link))
          spin = true
          break
        end
      end
    end
    spin || break
    spin = false
  end
end

const issues = []
querygithub() do json
  append!(issues, json)
end

### Markdown doc

repo(issue) = issue["repository"]["name"]
id(issue) = repo(issue) * "#" *  string(issue["number"])

sort!(issues; by=repo)

function issue2md(issue)
  url = issue["html_url"]
  title = strip(issue["title"])
  tags = join(map(x -> " #" * replace(x["name"], " " => "-"), issue["labels"]))
  "- [ ] [$(id(issue))]($url) :: $title$tags"
end

struct MD
  lines::Vector{String}
  issues::Dict{String,Int}
  inbox::UnitRange{Int}
end

function readmd(filename)
  lines = readlines(filename)
  issues = Dict{String,Int}()
  inboxstart = 0
  inboxend = 0
  for (i, s) ∈ enumerate(lines)
    s = strip(s)
    if startswith(s, "# ")
      inboxstart = i + 1
    elseif startswith(s, "## ")
      if lowercase(s) == "## inbox"
        inboxstart = i
      else
        inboxstart == 0 && (inboxstart = i - 1)
        inboxend == 0 && (inboxend = i)
      end
    elseif s == "---"
      inboxstart > 0 && inboxend == 0 && (inboxend = i)
    end
    m = match(r"^ *\- \[.\] +\[([A-Za-z0-9\.\-_]+#\d+)\]\(https://github.com/.*\)", s)
    if m !== nothing
      if m[1] ∈ keys(issues)
        @warn "Duplicate issue $(m[1]) on line $i (previously on line $(issues[m[1]]))"
      else
        issues[m[1]] = i
      end
    end
  end
  inboxstart > inboxend && (inboxend = length(lines) + 1)
  MD(lines, issues, inboxstart:inboxend)
end

function writemd(filename, issues, md=nothing)
  open(filename, "w") do io
    lines = deepcopy(md.lines)
    for (k, i) ∈ md.issues
      findfirst(issue -> id(issue) == k, issues) === nothing || continue
      lines[i] = replace(lines[i], "- [ ] " => "- [x] ")
    end
    if md !== nothing && first(md.inbox) > 0
      for i ∈ 1:first(md.inbox)-1
        println(io, lines[i])
      end
    end
    maybeclose = []
    println(io, "## INBOX")
    println(io)
    println(io, "### New issues")
    for issue ∈ issues
      newissue = true
      if md !== nothing
        if id(issue) ∈ keys(md.issues)
          lno = md.issues[id(issue)]
          if lno ∉ md.inbox
            newissue = false
            contains(lines[lno], "- [x] ") && push!(maybeclose, issue)
          end
        end
      end
      newissue && println(io, issue2md(issue))
    end
    println(io)
    if !isempty(maybeclose)
      println(io, "### Issues to close")
      for issue ∈ maybeclose
        url = issue["html_url"]
        println(io, "- [$(id(issue))]($url)")
      end
      println(io)
    end
    if md !== nothing
      for i ∈ max(last(md.inbox),1):length(lines)
        println(io, lines[i])
      end
    end
  end
end

let filename = expanduser(TASKDOC)
  md = readmd(filename)
  bakfile = joinpath(tempdir(), "github2md.bak")
  @info "Backup: $bakfile"
  open(bakfile, "w") do io
    println.(Ref(io), md.lines)
  end
  writemd(filename, issues, md)
end
