<template>
    <span id="user-avatar">
          <v-avatar  :title="fullname" :size="32">
            <img :src="src">
          </v-avatar>
    </span>
</template>

<script>
    import {lookup_icon} from "@/icons"
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
                        image = 'brandhorst_128.png';
                    }
                } else {
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
                    }
                }
                return img_dir + image
            },
        }
    }
</script>

<style scoped>
</style>