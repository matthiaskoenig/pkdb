<template>
      <v-avatar left :size="32" :title="fullname">
        <img :src="src" :alt=fullname>
      </v-avatar>
</template>

<script>
    export default {
        name: "UserAvatar",
        props: {
            search: {type:String, default:""},
            user: {
                type: Object,
                required: false,
            },
            username: {
                type: String,
                required: false,
            }
        },
        computed: {
            fullname() {
                if (this.user){
                    return this.user.first_name + ' ' + this.user.last_name;
                } else {
                    return this.username
                }
            },
            initials() {
                if (this.user){
                    return this.user.first_name[0] + this.user.last_name[0];
                } else {
                    return this.username
                }
            },
            src() {
                var img_dir = '/assets/images/avatars/';
                var image = 'anonymous_128.png';

                // FIXME: this is all hardcoded for now
                if (this.user){
                    image = 'user_128.png';
                    if (this.initials === 'MK'){
                        image = 'koenig_128.png';
                    } else if (this.initials === 'JG'){
                        image = 'grzegorzewski_128.png';
                    } else if (this.initials === 'KG'){
                        image = 'kgreen_128.png';
                    } else if (this.initials === 'DE'){
                        image = 'dimitra_128.png';
                    } else if (this.initials === 'DM'){
                        image = 'deepa_128.png';
                    } else if (this.initials === 'JB'){
                        image = 'jbrandhorst_128.png';
                    } else if (this.initials === 'YD'){
                        image = 'yduport_128.png';
                    } else if (this.initials === 'FB'){
                        image = 'FlorBar_128.png';
                    } else if (this.initials === 'AK'){
                        image = 'adrian_128.png';
                    } else if (this.initials === 'DK'){
                        image = 'danny_128.png';
                    } else if (this.initials === 'SD'){
                        image = 'sara_128.png';
                    } else if (this.initials === 'SB'){
                      image = 'balcisue_128.png';
                    } else if (this.initials === 'PO'){
                      image = 'paula_128.png';
                    } else if (this.initials === 'HL'){
                      image = 'lepujolh_128.png';
                    } else if (this.initials === 'BS'){
                      image = 'stemllb_128.png';
                    } else if (this.initials === 'JK'){
                      image = 'jonaspk98_128.png';
                    } else if (this.initials === 'XG'){
                      image = 'xresearch_128.png';
                    }
                } else if (this.username) {
                    image = 'user_128.png';
                    if (this.username === 'mkoenig'){
                        image = 'koenig_128.png';
                    } else if (this.username === 'janekg'){
                        image = 'grzegorzewski_128.png';
                    } else if (this.username === 'kgreen'){
                        image = 'kgreen_128.png';
                    } else if (this.username === 'dimitra'){
                        image = 'dimitra_128.png';
                    } else if (this.username === 'jbrandhorst'){
                        image = 'jbrandhorst_128.png';
                    } else if (this.username === 'deepa'){
                        image = 'deepa_128.png';
                    } else if (this.username === 'yduport'){
                        image = 'yduport_128.png';
                    } else if (this.username === 'FlorBar'){
                        image = 'FlorBar_128.png';
                    } else if (this.username === 'adriankl'){
                        image = 'adrian_128.png';
                    } else if (this.username === 'dannythekey'){
                        image = 'danny_128.png';
                    } else if (this.username === 'SaraD-hub'){
                        image = 'sara_128.png';
                    } else if (this.username === 'balcisue'){
                      image = 'balcisue_128.png';
                    } else if (this.username === 'paula-ogata'){
                      image = 'paula_128.png';
                    } else if (this.username === 'lepujolh'){
                      image = 'lepujolh_128.png';
                    } else if (this.username === 'stemllb'){
                      image = 'stemllb_128.png';
                    } else if (this.username === 'jonaspk98'){
                      image = 'jonaspk98_128.png';
                    } else if (this.username === 'xresearch'){
                      image = 'xresearch_128.png';
                    }
                }
                return img_dir + image
            },
        }
    }
</script>

<style scoped>
</style>