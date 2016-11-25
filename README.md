# denite-mpc

Neovim/Vim8 MPD client for browsing your music library by categories and filters
with the dark powered [denite.nvim] asynchronous interface framework.

## Features

- No dependencies (except [denite.nvim])
- Fast socket communication with MPD (_no_ need for `mpc`)
- Asynchronous [denite.nvim] gathering
- Add / play / replace selected
- Caching for large libraries
- Customizable formatting
- Multiple query filters

## Screenshot

![vim-denite-mpc screenshot](http://rafi.io/static/img/project/vim-denite-mpc/browsing.gif)

## Installation

### Requirements

- Vim or Neovim
- [denite.nvim]
- Python 3.4 or later

Use your favorite plugin manager, mine is [dein.vim], e.g.:

```sh
call dein#add('rafi/vim-denite-mpc', {'on_source': 'denite.nvim'})
```

## Usage

```viml
:Denite mpc:<tag>[:filterby:query:...]
```

Here are a few examples:

 Command | Description
-------- | -----------
`:Denite mpc:date` | Browse library by dates
`:Denite mpc:album:date:2016` | Browse albums, but just for year 2016
`:Denite mpc:artist:genre:Rock` | List all Rock (case-sensitive!) artists
`:Denite mpc:title:album:Blonde\ on\ Blonde` | List all track titles from an album
`:Denite mpc:album:genre:Electronic:date:2007` | You can combine filters

### Manage Playlist

You can view your current playlist:

```viml
:Denite mpc:playlist
```

### Actions

- `add` - Add selected items to playlist
- `play` - Add items and start playing
- `replace` - Clear playlist, add items, and start playing

The default action is `play`.

## Configuration

```viml
call denite#custom#var('mpc', 'host', 'localhost')
call denite#custom#var('mpc', 'port', 6600)
call denite#custom#var('mpc', 'timeout', 5.0)
call denite#custom#var('mpc', 'default_view', 'artist')
```

- The default values are shown.

## Planned Features

- [ ] Replace playlist with random songs
- [ ] Playlist items _(append/delete/replace)_
- [ ] Playlists management _(create/delete/load)_

## Credits & Contribution

This plugin was developed by Rafael Bodill under the MIT License.

Without [Shougo] this wouldn't be possible.

Pull requests are welcome.

[Shougo]: https://github.com/Shougo
[denite.nvim]: https://github.com/Shougo/denite.nvim
[dein.vim]: https://github.com/Shougo/dein.vim
