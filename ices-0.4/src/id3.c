/* id3.c
 * - Functions for id3 tags in ices
 * Copyright (c) 2000 Alexander Haväng
 * Copyright (c) 2001-3 Brendan Cully <brendan@icecast.org>
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
 *
 */

#include "definitions.h"
#include "metadata.h"

/* Local definitions */
typedef struct {
  unsigned char major_version;
  unsigned char minor_version;
  unsigned char flags;
  size_t len;

  char* artist;
  char* title;

  unsigned int pos;
} id3v2_tag;

typedef struct {
  size_t frame_len;
  const char* artist_tag;
  const char* title_tag;
} id3v2_version_info;

static id3v2_version_info vi[5] = {
  {  6, "TP1", "TT2" },
  {  6, "TP1", "TT2" },
  {  6, "TP1", "TT2" },
  { 10, "TPE1", "TIT2" },
  { 10, "TPE1", "TIT2" }
};

#define ID3V2_FLAG_UNSYNC (1<<7)
#define ID3V2_FLAG_EXTHDR (1<<6)
#define ID3V2_FLAG_EXPHDR (1<<5)
#define ID3V2_FLAG_FOOTER (1<<4)

#define ID3V2_FRAME_LEN(tagp) (vi[(tagp)->major_version].frame_len)
#define ID3V2_ARTIST_TAG(tagp) (vi[(tagp)->major_version].artist_tag)
#define ID3V2_TITLE_TAG(tagp) (vi[(tagp)->major_version].title_tag)

/* Private function declarations */
static int id3v2_read_exthdr (input_stream_t* source, id3v2_tag* tag);
ssize_t id3v2_read_frame (input_stream_t* source, id3v2_tag* tag);
static int id3v2_skip_data (input_stream_t* source, id3v2_tag* tag, size_t len);
static int id3v2_decode_synchsafe (unsigned char* synchsafe);
static int id3v2_decode_synchsafe3 (unsigned char* synchsafe);
static int id3v2_decode_unsafe (unsigned char* in);

/* Global function definitions */

void
ices_id3v1_parse (input_stream_t* source)
{
  off_t pos;
  char buffer[1024];
  char title[31];
  int i;

  if (! source->filesize)
    return;

  buffer[30] = '\0';
  title[30] = '\0';
  pos = lseek (source->fd, 0, SEEK_CUR);

  lseek (source->fd, -128, SEEK_END);

  if ((read (source->fd, buffer, 3) == 3) && !strncmp (buffer, "TAG", 3)) {
    /* Don't stream the tag */
    source->filesize -= 128;

    if (read (source->fd, title, 30) != 30) {
      ices_log ("Error reading ID3v1 song title: %s",
        ices_util_strerror (errno, buffer, sizeof (buffer)));
      goto out;
    }

    for (i = strlen (title) - 1; i >= 0 && title[i] == ' '; i--)
      title[i] = '\0';
    ices_log_debug ("ID3v1: Title: %s", title);

    if (read (source->fd, buffer, 30) != 30) {
      ices_log ("Error reading ID3v1 artist: %s",
        ices_util_strerror (errno, buffer, sizeof (buffer)));
      goto out;
    }

    for (i = strlen (buffer) - 1; i >= 0 && buffer[i] == ' '; i--)
      buffer[i] = '\0';
    ices_log_debug ("ID3v1: Artist: %s", buffer);

    ices_metadata_set (buffer, title);
  }
  
out:
  lseek (source->fd, pos, SEEK_SET);
}

void
ices_id3v2_parse (input_stream_t* source)
{
  unsigned char buf[1024];
  id3v2_tag tag;
  size_t remaining;
  ssize_t rv;

  if (source->read (source, buf, 10) != 10) {
    ices_log ("Error reading ID3v2");

    return;
  }

  tag.artist = tag.title = NULL;
  tag.pos = 0;
  tag.major_version = *(buf + 3);
  tag.minor_version = *(buf + 4);
  tag.flags = *(buf + 5);
  tag.len = id3v2_decode_synchsafe (buf + 6);
  ices_log_debug ("ID3v2: version %d.%d. Tag size is %d bytes.",
                  tag.major_version, tag.minor_version, tag.len);
  if (tag.major_version > 4) {
    ices_log_debug ("ID3v2: Version greater than maximum supported (4), skipping");
    id3v2_skip_data (source, &tag, tag.len);

    return;
  }

  if ((tag.major_version > 2) &&
      (tag.flags & ID3V2_FLAG_EXTHDR) && id3v2_read_exthdr (source, &tag) < 0) {
    ices_log ("Error reading ID3v2 extended header");

    return;
  }

  remaining = tag.len - tag.pos;
  if ((tag.major_version > 3) && (tag.flags & ID3V2_FLAG_FOOTER))
    remaining -= 10;

  while (remaining > ID3V2_FRAME_LEN(&tag) && (tag.artist == NULL || tag.title == NULL)) {
    if ((rv = id3v2_read_frame (source, &tag)) < 0) {
      ices_log ("Error reading ID3v2 frames, skipping to end of ID3v2 tag");
      break;
    }
    /* found padding */
    if (rv == 0)
      break;

    remaining -= rv;
  }

  /* allow fallback to ID3v1 */
  if (tag.artist || tag.title)
    ices_metadata_set (tag.artist, tag.title);
  ices_util_free (tag.artist);
  ices_util_free (tag.title);

  remaining = tag.len - tag.pos;
  if (remaining)
    id3v2_skip_data (source, &tag, remaining);
}

static int
id3v2_read_exthdr (input_stream_t* source, id3v2_tag* tag)
{
  char hdr[6];
  size_t len;

  if (source->read (source, hdr, 6) != 6) {
    ices_log ("Error reading ID3v2 extended header");

    return -1;
  }
  tag->pos += 6;

  len = id3v2_decode_synchsafe (hdr);
  ices_log_debug ("ID3v2: %d byte extended header found, skipping.", len);

  if (len > 6)
    return id3v2_skip_data (source, tag, len - 6);
  else
    return 0;
}

ssize_t
id3v2_read_frame (input_stream_t* source, id3v2_tag* tag)
{
  char hdr[10];
  size_t len, len2;
  ssize_t rlen;
  char* buf;

  if (source->read (source, hdr, ID3V2_FRAME_LEN(tag)) != ID3V2_FRAME_LEN(tag)) {
    ices_log ("Error reading ID3v2 frame");

    return -1;
  }
  tag->pos += ID3V2_FRAME_LEN(tag);

  if (hdr[0] == '\0')
    return 0;

  if (tag->major_version < 3) {
    len = id3v2_decode_synchsafe3 (hdr + 3);
    hdr[3] = '\0';
  } else if (tag->major_version == 3) {
    len = id3v2_decode_unsafe (hdr + 4);
    hdr[4] = '\0';
  } else {
    len = id3v2_decode_synchsafe (hdr + 4);
    hdr[4] = '\0';
  }
  if (len > tag->len - tag->pos) {
    ices_log ("Error parsing ID3v2 frame header: Frame too large (%d bytes)", len);
    
    return -1;
  }

  /* ices_log_debug("ID3v2: Frame type [%s] found, %d bytes", hdr, len); */
  if (!strcmp (hdr, ID3V2_ARTIST_TAG(tag)) || !strcmp (hdr, ID3V2_TITLE_TAG(tag))) {
    if (! (buf = malloc(len+1))) {
      ices_log ("Error allocating memory while reading ID3v2 frame");
      
      return -1;
    }
    len2 = len;
    while (len2) {
      if ((rlen = source->read (source, buf, len)) < 0) {
        ices_log ("Error reading ID3v2 frame data");
        free (buf);
      
        return -1;
      }
      tag->pos += rlen;
      len2 -= rlen;
    }

    /* skip encoding */
    if (!strcmp (hdr, ID3V2_TITLE_TAG(tag))) {
      buf[len] = '\0';
      ices_log_debug ("ID3v2: Title found: %s", buf + 1);
      tag->title = ices_util_strdup (buf + 1);
    } else {
      buf[len] = '\0';
      ices_log_debug ("ID3v2: Artist found: %s", buf + 1);
      tag->artist = ices_util_strdup (buf + 1);
    }

    free (buf);
  } else if (id3v2_skip_data (source, tag, len))
    return -1;

  return len + ID3V2_FRAME_LEN(tag);
}

static int
id3v2_skip_data (input_stream_t* source, id3v2_tag* tag, size_t len)
{
  char* buf;
  ssize_t rlen;

  if (! (buf = malloc(len))) {
    ices_log ("Error allocating memory while skipping ID3v2 data");
    
    return -1;
  }

  while (len) {
    if ((rlen = source->read (source, buf, len)) < 0) {
      ices_log ("Error skipping in ID3v2 tag.");
      free (buf);

      return -1;
    }
    tag->pos += rlen;
    len -= rlen;
  }

  free (buf);

  return 0;
}

static int
id3v2_decode_synchsafe (unsigned char* synchsafe)
{
  int res;

  res = synchsafe[3];
  res |= synchsafe[2] << 7;
  res |= synchsafe[1] << 14;
  res |= synchsafe[0] << 21;

  return res;
}

static int
id3v2_decode_synchsafe3 (unsigned char* synchsafe)
{
  int res;

  res = synchsafe[2];
  res |= synchsafe[1] << 7;
  res |= synchsafe[0] << 14;

  return res;
}

/* id3v2.3 badly specifies frame length */
static int
id3v2_decode_unsafe (unsigned char* in)
{
  int res;

  res = in[3];
  res |= in[2] << 8;
  res |= in[1] << 16;
  res |= in[0] << 24;

  return res;
}
